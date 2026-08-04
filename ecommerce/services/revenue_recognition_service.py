from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finance.models import CustomerAdvance, JournalEntry, LedgerAccount
from finance.services.customer_advance_service import CustomerAdvanceService
from finance.services.general_ledger_service import GeneralLedgerService
from orders.models import Order

from ..models import (
    EcommerceCheckout,
    EcommerceCheckoutOrder,
    EcommercePayment,
    MarketplaceOrderLine,
)


class EcommerceRevenueRecognitionService:
    """Recognizes Ecommerce revenue and independent-seller obligations."""

    EARNED_ORDER_STATUSES = {"DELIVERED", "COMPLETED"}
    CUSTOMER_ADVANCES_ACCOUNT = "2100"
    SELLER_PAYABLE_ACCOUNT = "2200"
    MARKETPLACE_COMMISSION_ACCOUNT = "4400"
    ZERO = Decimal("0.00")

    @classmethod
    def _account(cls, code, expected_type=None):
        account = CustomerAdvanceService._account(code)
        if expected_type and account.account_type != expected_type:
            raise ValidationError(
                f"Ledger account {account.code} must be a "
                f"{expected_type.lower()} account."
            )
        return account

    @classmethod
    def _marketplace_lines(cls, order):
        order_items = list(order.items.order_by("pk"))
        lines = list(
            MarketplaceOrderLine.objects
            .select_for_update()
            .filter(order_item__order_id=order.pk)
            .order_by("order_item_id")
        )

        item_ids = {item.pk for item in order_items}
        snapshot_item_ids = {line.order_item_id for line in lines}
        missing_ids = item_ids - snapshot_item_ids

        if missing_ids:
            missing_names = [
                item.product_name
                for item in order_items
                if item.pk in missing_ids
            ]
            raise ValidationError(
                (
                    "Marketplace seller snapshots are missing for: "
                    f"{', '.join(missing_names)}."
                )
            )

        if len(lines) != len(order_items):
            raise ValidationError(
                "Marketplace seller snapshots do not match the order items."
            )

        return lines

    @classmethod
    def _posting_lines(cls, *, order, marketplace_lines):
        advances_account = cls._account(
            cls.CUSTOMER_ADVANCES_ACCOUNT,
            LedgerAccount.LIABILITY,
        )
        default_payable_account = cls._account(
            cls.SELLER_PAYABLE_ACCOUNT,
            LedgerAccount.LIABILITY,
        )
        commission_account = cls._account(
            cls.MARKETPLACE_COMMISSION_ACCOUNT,
            LedgerAccount.REVENUE,
        )
        _, business_revenue_account = (
            CustomerAdvanceService._revenue_account(
                order.business_unit
            )
        )

        internal_revenue = cls.ZERO
        commission_revenue = cls.ZERO
        seller_payables = defaultdict(lambda: cls.ZERO)
        payable_accounts = {}

        for line in marketplace_lines:
            if line.seller.is_internal:
                if line.commission_amount != cls.ZERO:
                    raise ValidationError(
                        (
                            f"Internal seller line {line.pk} cannot have "
                            "a Marketplace commission."
                        )
                    )
                internal_revenue += line.gross_amount
                continue

            if line.seller_net_amount <= cls.ZERO:
                raise ValidationError(
                    f"Independent seller line {line.pk} has no payable amount."
                )

            payable_account = (
                line.seller.payable_account
                or default_payable_account
            )
            if payable_account.account_type != LedgerAccount.LIABILITY:
                raise ValidationError(
                    f"Seller payable account {payable_account.code} "
                    "must be a liability account."
                )
            if not payable_account.is_active:
                raise ValidationError(
                    f"Seller payable account {payable_account.code} is inactive."
                )

            payable_accounts[payable_account.pk] = payable_account
            seller_payables[payable_account.pk] += line.seller_net_amount
            commission_revenue += line.commission_amount

        recognized_amount = sum(
            (line.gross_amount for line in marketplace_lines),
            cls.ZERO,
        )
        credits = internal_revenue + commission_revenue + sum(
            seller_payables.values(),
            cls.ZERO,
        )

        if credits != recognized_amount:
            raise ValidationError(
                "Marketplace revenue allocation is not balanced."
            )

        posting_lines = [
            {
                "account": advances_account,
                "debit": recognized_amount,
                "description": (
                    f"Release advance liability — {order.order_number}"
                ),
            }
        ]

        if internal_revenue > cls.ZERO:
            posting_lines.append(
                {
                    "account": business_revenue_account,
                    "credit": internal_revenue,
                    "description": (
                        f"WPG revenue earned — {order.order_number}"
                    ),
                }
            )

        for account_id, amount in sorted(seller_payables.items()):
            posting_lines.append(
                {
                    "account": payable_accounts[account_id],
                    "credit": amount,
                    "description": (
                        f"Marketplace seller obligations — "
                        f"{order.order_number}"
                    ),
                }
            )

        if commission_revenue > cls.ZERO:
            posting_lines.append(
                {
                    "account": commission_account,
                    "credit": commission_revenue,
                    "description": (
                        f"Marketplace commission earned — "
                        f"{order.order_number}"
                    ),
                }
            )

        return {
            "lines": posting_lines,
            "recognized_amount": recognized_amount,
            "internal_revenue": internal_revenue,
            "commission_revenue": commission_revenue,
            "seller_payable": sum(
                seller_payables.values(),
                cls.ZERO,
            ),
        }

    @classmethod
    @transaction.atomic
    def recognize_delivered_order(cls, *, order, actor=None):
        if not isinstance(order, Order) or not order.pk:
            raise ValidationError("A saved Enterprise Order is required.")

        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status not in cls.EARNED_ORDER_STATUSES:
            raise ValidationError(
                f"Order {order.order_number} must be delivered before "
                "Ecommerce revenue can be recognized."
            )

        try:
            checkout_link = (
                EcommerceCheckoutOrder.objects
                .select_for_update()
                .get(order_id=order.pk)
            )
        except EcommerceCheckoutOrder.DoesNotExist as error:
            raise ValidationError(
                f"Order {order.order_number} is not an Ecommerce order."
            ) from error

        checkout = EcommerceCheckout.objects.select_for_update().get(
            pk=checkout_link.checkout_id
        )
        payment = (
            EcommercePayment.objects
            .select_for_update()
            .filter(
                checkout_id=checkout.pk,
                status=EcommercePayment.CONFIRMED,
            )
            .first()
        )
        if payment is None:
            raise ValidationError(
                f"Checkout {checkout.checkout_number} has no confirmed payment."
            )
        if payment.customer_advance_id is None:
            raise ValidationError(
                f"Payment {payment.payment_number} has no Customer Advance."
            )

        advance = CustomerAdvance.objects.select_for_update().get(
            pk=payment.customer_advance_id
        )
        if advance.status in {
            CustomerAdvance.PENDING,
            CustomerAdvance.CANCELLED,
            CustomerAdvance.REFUNDED,
        }:
            raise ValidationError(
                f"Advance {advance.reference} cannot be applied while it is "
                f"{advance.get_status_display()}."
            )

        source_type = "ECOMMERCE_ORDER_DELIVERY"
        source_id = str(order.pk)
        source_key = (
            f"CUSTOMER_ADVANCE_APPLICATION:{advance.pk}:"
            f"{source_type}:{source_id}"
        )
        existing_entry = JournalEntry.objects.filter(
            source_key=source_key
        ).first()
        if existing_entry is not None:
            if existing_entry.status != JournalEntry.POSTED:
                raise ValidationError(
                    "An incomplete delivery journal already exists."
                )
            cls._synchronize_checkout_status(checkout)
            return {
                "order": order,
                "checkout": checkout,
                "checkout_link": checkout_link,
                "payment": payment,
                "advance": advance,
                "journal_entry": existing_entry,
                "created": False,
                "amount": checkout_link.amount,
                "business_unit": checkout_link.business_unit,
            }

        marketplace_lines = cls._marketplace_lines(order)
        allocation = cls._posting_lines(
            order=order,
            marketplace_lines=marketplace_lines,
        )
        amount = allocation["recognized_amount"]

        if amount != checkout_link.amount:
            raise ValidationError(
                (
                    f"Marketplace item snapshots total {amount} RWF, but "
                    f"checkout order amount is {checkout_link.amount} RWF. "
                    "Discount and tax allocation must be implemented before "
                    "this order can be recognized."
                )
            )
        if amount > advance.available_amount:
            raise ValidationError(
                {
                    "amount": (
                        f"Only {advance.available_amount} "
                        f"{advance.currency} remains available."
                    )
                }
            )

        entry, created = GeneralLedgerService.create_and_post(
            description=(
                f"Recognize Ecommerce delivery {order.order_number}"
            ),
            lines=allocation["lines"],
            entry_date=timezone.localdate(),
            business_unit=order.business_unit,
            source_type=source_type,
            source_id=source_id,
            source_reference=order.order_number,
            source_key=source_key,
            actor=actor,
        )

        if created:
            advance.applied_amount += amount
            CustomerAdvanceService._set_status(advance)
            advance.full_clean()
            advance.save(
                update_fields=[
                    "applied_amount",
                    "status",
                    "updated_at",
                ]
            )

            now = timezone.now()
            for line in marketplace_lines:
                if line.seller.is_internal:
                    line.settlement_status = MarketplaceOrderLine.SETTLED
                    line.eligible_at = None
                else:
                    line.settlement_status = MarketplaceOrderLine.ELIGIBLE
                    line.eligible_at = now
                line.save(
                    update_fields=[
                        "settlement_status",
                        "eligible_at",
                        "updated_at",
                    ]
                )

            CustomerAdvanceService._dispatch(
                event_code="FINANCE_CUSTOMER_ADVANCE_APPLIED",
                advance=advance,
                actor=actor,
                title="Ecommerce Delivery Revenue Recognized",
                message=(
                    f"{amount} RWF from {advance.reference} was applied "
                    f"for order {order.order_number}."
                ),
                metadata={
                    "journal_entry_id": entry.pk,
                    "order_id": order.pk,
                    "business_unit": order.business_unit,
                    "internal_revenue": str(allocation["internal_revenue"]),
                    "seller_payable": str(allocation["seller_payable"]),
                    "commission_revenue": str(
                        allocation["commission_revenue"]
                    ),
                },
            )

        cls._synchronize_checkout_status(checkout)

        return {
            "order": order,
            "checkout": checkout,
            "checkout_link": checkout_link,
            "payment": payment,
            "advance": advance,
            "journal_entry": entry,
            "created": created,
            "amount": amount,
            "business_unit": order.business_unit,
            "internal_revenue": allocation["internal_revenue"],
            "seller_payable": allocation["seller_payable"],
            "commission_revenue": allocation["commission_revenue"],
        }

    @classmethod
    def _synchronize_checkout_status(cls, checkout):
        statuses = list(
            checkout.checkout_orders.values_list(
                "order__status",
                flat=True,
            )
        )
        if not statuses:
            return checkout

        delivered = [
            status in cls.EARNED_ORDER_STATUSES
            for status in statuses
        ]

        if all(delivered):
            checkout.status = "COMPLETED"
            if checkout.completed_at is None:
                checkout.completed_at = timezone.now()
            checkout.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "updated_at",
                ]
            )
        elif any(delivered):
            checkout.status = "PARTIAL"
            checkout.save(
                update_fields=["status", "updated_at"]
            )

        return checkout
