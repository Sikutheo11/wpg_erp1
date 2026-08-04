from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine
from finance.models import JournalEntry, LedgerAccount
from finance.services.customer_advance_service import CustomerAdvanceService
from finance.services.general_ledger_service import GeneralLedgerService

from ..models import (
    MarketplaceOrderLine,
    MarketplaceSeller,
    SellerSettlement,
    SellerSettlementLine,
)


class SellerSettlementService:
    """Creates, approves and pays independent Marketplace seller balances."""

    SELLER_PAYABLE_ACCOUNT = "2200"
    ZERO = Decimal("0.00")

    @staticmethod
    def _user(actor):
        if actor is None:
            return None
        if hasattr(actor, "is_authenticated"):
            return actor
        return getattr(actor, "user", None)

    @classmethod
    def _dispatch(
        cls,
        *,
        event_code,
        settlement,
        actor,
        title,
        message,
        metadata=None,
    ):
        event_metadata = {
            "settlement_id": settlement.pk,
            "settlement_number": settlement.settlement_number,
            "seller_id": settlement.seller_id,
            "seller_name": settlement.seller.name,
            "status": settlement.status,
            "total_gross": str(settlement.total_gross),
            "total_commission": str(settlement.total_commission),
            "total_payable": str(settlement.total_payable),
        }
        if metadata:
            event_metadata.update(metadata)

        EventEngine.dispatch(
            event_code=event_code,
            actor=cls._user(actor),
            obj=settlement,
            title=title,
            message=message,
            level="SUCCESS",
            metadata=event_metadata,
            notify_groups=["Finance Manager", "Marketplace Manager"],
            notify_owner=True,
        )

    @classmethod
    def _validate_seller(cls, seller):
        if not isinstance(seller, MarketplaceSeller) or not seller.pk:
            raise ValidationError("A saved Marketplace seller is required.")
        if not seller.is_active:
            raise ValidationError(f"Seller {seller.name} is inactive.")
        if seller.is_internal:
            raise ValidationError(
                "WPG-owned sellers do not require Marketplace settlements."
            )

    @classmethod
    @transaction.atomic
    def create_settlement(
        cls,
        *,
        seller,
        line_ids=None,
        actor=None,
        notes="",
    ):
        cls._validate_seller(seller)
        seller = MarketplaceSeller.objects.select_for_update().get(
            pk=seller.pk
        )

        eligible_lines = (
            MarketplaceOrderLine.objects
            .select_for_update()
            .filter(
                seller=seller,
                settlement_status=MarketplaceOrderLine.ELIGIBLE,
            )
            .exclude(
                pk__in=SellerSettlementLine.objects.values(
                    "marketplace_order_line_id"
                )
            )
            .order_by("pk")
        )
        if line_ids is not None:
            normalized_ids = {
                int(line_id)
                for line_id in line_ids
            }
            if not normalized_ids:
                raise ValidationError("Select at least one eligible sale line.")
            eligible_lines = eligible_lines.filter(pk__in=normalized_ids)

        lines = list(eligible_lines)
        if not lines:
            raise ValidationError(
                f"Seller {seller.name} has no eligible sales to settle."
            )

        total_gross = sum(
            (line.gross_amount for line in lines),
            cls.ZERO,
        )
        total_commission = sum(
            (line.commission_amount for line in lines),
            cls.ZERO,
        )
        total_payable = sum(
            (line.seller_net_amount for line in lines),
            cls.ZERO,
        )

        settlement = SellerSettlement(
            seller=seller,
            status=SellerSettlement.DRAFT,
            total_gross=total_gross,
            total_commission=total_commission,
            total_payable=total_payable,
            notes=(notes or "").strip(),
            created_by=cls._user(actor),
        )
        settlement.full_clean()
        settlement.save()

        settlement_lines = [
            SellerSettlementLine(
                settlement=settlement,
                marketplace_order_line=line,
                gross_amount=line.gross_amount,
                commission_amount=line.commission_amount,
                payable_amount=line.seller_net_amount,
            )
            for line in lines
        ]
        for settlement_line in settlement_lines:
            settlement_line.full_clean()
        SellerSettlementLine.objects.bulk_create(settlement_lines)

        MarketplaceOrderLine.objects.filter(
            pk__in=[line.pk for line in lines],
            settlement_status=MarketplaceOrderLine.ELIGIBLE,
        ).update(
            settlement_status=MarketplaceOrderLine.IN_SETTLEMENT,
            updated_at=timezone.now(),
        )

        cls._dispatch(
            event_code="MARKETPLACE_SETTLEMENT_CREATED",
            settlement=settlement,
            actor=actor,
            title="Seller Settlement Created",
            message=(
                f"Settlement {settlement.settlement_number} was created "
                f"for {seller.name}."
            ),
            metadata={"sale_line_ids": [line.pk for line in lines]},
        )
        return settlement

    @classmethod
    @transaction.atomic
    def approve_settlement(cls, *, settlement, actor=None):
        if not isinstance(settlement, SellerSettlement) or not settlement.pk:
            raise ValidationError("A saved seller settlement is required.")

        settlement = SellerSettlement.objects.select_for_update().get(
            pk=settlement.pk
        )
        if settlement.status == SellerSettlement.APPROVED:
            return settlement, False
        if settlement.status != SellerSettlement.DRAFT:
            raise ValidationError(
                f"Settlement {settlement.settlement_number} cannot be approved "
                f"from status {settlement.get_status_display()}."
            )
        if not settlement.lines.exists():
            raise ValidationError("A settlement must contain at least one line.")
        if settlement.total_payable <= cls.ZERO:
            raise ValidationError("Settlement payable amount must be positive.")

        settlement.status = SellerSettlement.APPROVED
        settlement.approved_by = cls._user(actor)
        settlement.approved_at = timezone.now()
        settlement.full_clean()
        settlement.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

        cls._dispatch(
            event_code="MARKETPLACE_SETTLEMENT_APPROVED",
            settlement=settlement,
            actor=actor,
            title="Seller Settlement Approved",
            message=(
                f"Settlement {settlement.settlement_number} for "
                f"{settlement.total_payable} RWF was approved."
            ),
        )
        return settlement, True

    @classmethod
    @transaction.atomic
    def pay_settlement(
        cls,
        *,
        settlement,
        payment_method=None,
        payment_account_code=None,
        payment_reference="",
        payment_date=None,
        actor=None,
    ):
        if not isinstance(settlement, SellerSettlement) or not settlement.pk:
            raise ValidationError("A saved seller settlement is required.")

        settlement = SellerSettlement.objects.select_for_update().get(
            pk=settlement.pk
        )
        if settlement.status == SellerSettlement.PAID:
            if settlement.journal_entry_id is None:
                raise ValidationError(
                    "Paid settlement has no Finance journal entry."
                )
            return settlement, False
        if settlement.status != SellerSettlement.APPROVED:
            raise ValidationError(
                f"Settlement {settlement.settlement_number} must be approved "
                "before payment."
            )

        seller = MarketplaceSeller.objects.get(pk=settlement.seller_id)
        cls._validate_seller(seller)
        payment_account = CustomerAdvanceService._payment_account(
            payment_method=payment_method,
            account_code=payment_account_code,
        )
        payable_account = seller.payable_account
        if payable_account is None:
            payable_account = CustomerAdvanceService._account(
                cls.SELLER_PAYABLE_ACCOUNT
            )
        if payable_account.account_type != LedgerAccount.LIABILITY:
            raise ValidationError(
                f"Seller payable account {payable_account.code} must be a "
                "liability account."
            )

        source_key = f"MARKETPLACE_SETTLEMENT_PAYMENT:{settlement.pk}"
        entry, created = GeneralLedgerService.create_and_post(
            description=(
                f"Pay Marketplace settlement "
                f"{settlement.settlement_number} to {seller.name}"
            ),
            lines=[
                {
                    "account": payable_account,
                    "debit": settlement.total_payable,
                    "description": (
                        f"Clear seller payable — "
                        f"{settlement.settlement_number}"
                    ),
                },
                {
                    "account": payment_account,
                    "credit": settlement.total_payable,
                    "description": (
                        f"Payment to {seller.name} — "
                        f"{settlement.settlement_number}"
                    ),
                },
            ],
            entry_date=payment_date or timezone.localdate(),
            business_unit="MARKETPLACE",
            source_type="MARKETPLACE_SELLER_SETTLEMENT",
            source_id=str(settlement.pk),
            source_reference=settlement.settlement_number,
            source_key=source_key,
            actor=actor,
        )

        if created:
            settlement.status = SellerSettlement.PAID
            settlement.payment_reference = (
                payment_reference or ""
            ).strip()
            settlement.journal_entry = entry
            settlement.paid_by = cls._user(actor)
            settlement.paid_at = timezone.now()
            settlement.save(
                update_fields=[
                    "status",
                    "payment_reference",
                    "journal_entry",
                    "paid_by",
                    "paid_at",
                    "updated_at",
                ]
            )

            MarketplaceOrderLine.objects.filter(
                settlement_line__settlement=settlement,
                settlement_status=MarketplaceOrderLine.IN_SETTLEMENT,
            ).update(
                settlement_status=MarketplaceOrderLine.SETTLED,
                updated_at=timezone.now(),
            )

            cls._dispatch(
                event_code="MARKETPLACE_SETTLEMENT_PAID",
                settlement=settlement,
                actor=actor,
                title="Seller Settlement Paid",
                message=(
                    f"{settlement.total_payable} RWF was paid to "
                    f"{seller.name}."
                ),
                metadata={
                    "journal_entry_id": entry.pk,
                    "payment_account_code": payment_account.code,
                    "payable_account_code": payable_account.code,
                    "payment_reference": settlement.payment_reference,
                },
            )

        return settlement, created

    @classmethod
    @transaction.atomic
    def cancel_settlement(
        cls,
        *,
        settlement,
        actor=None,
        reason="",
    ):
        """
        Cancel an unpaid settlement and return its sale lines to ELIGIBLE.

        Paid settlements cannot be cancelled because their payment journal
        must instead be handled through an explicit reversal workflow.
        """
        if not isinstance(settlement, SellerSettlement) or not settlement.pk:
            raise ValidationError("A saved seller settlement is required.")

        settlement = SellerSettlement.objects.select_for_update().get(
            pk=settlement.pk
        )

        if settlement.status == SellerSettlement.CANCELLED:
            return settlement, False

        if settlement.status not in {
            SellerSettlement.DRAFT,
            SellerSettlement.APPROVED,
        }:
            raise ValidationError(
                f"Settlement {settlement.settlement_number} cannot be "
                f"cancelled from status {settlement.get_status_display()}."
            )

        reason = (reason or "").strip()
        if not reason:
            raise ValidationError("A cancellation reason is required.")

        settlement.status = SellerSettlement.CANCELLED
        settlement.notes = (
            f"{settlement.notes}\nCancellation reason: {reason}"
            if settlement.notes
            else f"Cancellation reason: {reason}"
        )
        settlement.save(
            update_fields=[
                "status",
                "notes",
                "updated_at",
            ]
        )

        released_line_ids = list(
            settlement.lines.values_list(
                "marketplace_order_line_id",
                flat=True,
            )
        )

        released_count = MarketplaceOrderLine.objects.filter(
            pk__in=released_line_ids,
            settlement_status=MarketplaceOrderLine.IN_SETTLEMENT,
        ).update(
            settlement_status=MarketplaceOrderLine.ELIGIBLE,
            updated_at=timezone.now(),
        )

        # The OneToOne settlement link must be removed so a released sale
        # line can be selected for a future settlement. The cancelled
        # settlement retains its totals, seller, notes and audit timestamps.
        settlement.lines.all().delete()

        cls._dispatch(
            event_code="MARKETPLACE_SETTLEMENT_CANCELLED",
            settlement=settlement,
            actor=actor,
            title="Seller Settlement Cancelled",
            message=(
                f"Settlement {settlement.settlement_number} was cancelled. "
                f"{released_count} sale line(s) returned to eligibility."
            ),
            metadata={
                "reason": reason,
                "released_line_count": released_count,
                "released_line_ids": released_line_ids,
            },
        )

        return settlement, True
