from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine
from finance.services.customer_advance_service import (
    CustomerAdvanceService,
)
from orders.services import OrderService

from ..models import EcommerceCheckout, EcommercePayment


class EcommercePaymentService:
    """
    Coordinates Marketplace payment confirmation.

    A checkout is created with PENDING Enterprise Orders. Those orders are
    confirmed only after payment has been confirmed and Finance has posted
    the money as a Customer Advance.
    """

    FINANCE_PAYMENT_METHODS = {
        EcommercePayment.CASH: "cash",
        EcommercePayment.BANK: "bank",
        EcommercePayment.MOBILE_MONEY: "mobile_money",
    }

    @staticmethod
    def _user(actor):
        if actor is None:
            return None
        if hasattr(actor, "is_authenticated"):
            return actor
        return getattr(actor, "user", None)

    @staticmethod
    def _required(value, field_name):
        value = str(value or "").strip()
        if not value:
            raise ValidationError(
                {field_name: f"{field_name.replace('_', ' ').title()} is required."}
            )
        return value

    @classmethod
    def _dispatch(
        cls,
        *,
        event_code,
        payment,
        actor,
        title,
        message,
        level="INFO",
        metadata=None,
    ):
        EventEngine.dispatch(
            event_code=event_code,
            actor=cls._user(actor),
            obj=payment,
            title=title,
            message=message,
            level=level,
            metadata={
                "payment_id": payment.pk,
                "payment_number": payment.payment_number,
                "checkout_id": payment.checkout_id,
                "checkout_number": payment.checkout.checkout_number,
                "amount": str(payment.amount),
                "method": payment.method,
                "provider": payment.provider,
                "provider_reference": payment.provider_reference,
                **(metadata or {}),
            },
            notify_groups=["Finance Manager", "Order Manager"],
            notify_owner=True,
        )

    @classmethod
    @transaction.atomic
    def initiate_payment(
        cls,
        *,
        checkout,
        method,
        provider="",
        customer_reference="",
        idempotency_key=None,
        proof_image=None,
        notes="",
        actor=None,
    ):
        """Create one payment attempt for the full checkout amount."""
        if not isinstance(checkout, EcommerceCheckout) or not checkout.pk:
            raise ValidationError("A saved Ecommerce checkout is required.")

        method = cls._required(method, "method").upper()
        valid_methods = {choice[0] for choice in EcommercePayment.METHODS}
        if method not in valid_methods:
            raise ValidationError({"method": "Unsupported payment method."})

        idempotency_key = (idempotency_key or "").strip() or None
        if idempotency_key:
            existing = (
                EcommercePayment.objects
                .select_related("checkout")
                .filter(idempotency_key=idempotency_key)
                .first()
            )
            if existing is not None:
                if existing.checkout_id != checkout.pk:
                    raise ValidationError(
                        "This idempotency key belongs to another checkout."
                    )
                return existing, False

        # Lock only the checkout table. Joining nullable relations to a
        # SELECT FOR UPDATE query would fail on PostgreSQL.
        checkout = EcommerceCheckout.objects.select_for_update().get(
            pk=checkout.pk
        )

        if checkout.status in {"CANCELLED", "FAILED", "COMPLETED"}:
            raise ValidationError(
                f"Checkout {checkout.checkout_number} cannot accept payment "
                f"while it is {checkout.get_status_display()}."
            )
        if checkout.total_amount <= 0:
            raise ValidationError("Checkout total must be greater than zero.")
        if checkout.payments.filter(status=EcommercePayment.CONFIRMED).exists():
            raise ValidationError("This checkout has already been paid.")

        payment = EcommercePayment(
            checkout=checkout,
            method=method,
            status=EcommercePayment.INITIATED,
            amount=checkout.total_amount,
            currency=checkout.currency,
            provider=(provider or "").strip(),
            customer_reference=(customer_reference or "").strip(),
            idempotency_key=idempotency_key,
            proof_image=proof_image,
            notes=(notes or "").strip(),
            initiated_by=cls._user(actor),
        )
        payment.full_clean()
        payment.save()

        cls._dispatch(
            event_code="ECOMMERCE_PAYMENT_INITIATED",
            payment=payment,
            actor=actor,
            title="Ecommerce Payment Initiated",
            message=(
                f"Payment {payment.payment_number} was initiated for "
                f"checkout {checkout.checkout_number}."
            ),
        )
        return payment, True

    @classmethod
    @transaction.atomic
    def mark_pending(
        cls,
        *,
        payment,
        provider_reference="",
        actor=None,
    ):
        """Mark a provider request as sent and awaiting confirmation."""
        if not isinstance(payment, EcommercePayment) or not payment.pk:
            raise ValidationError("A saved Ecommerce payment is required.")

        payment = EcommercePayment.objects.select_for_update().get(
            pk=payment.pk
        )
        if payment.status == EcommercePayment.PENDING:
            return payment, False
        if payment.status != EcommercePayment.INITIATED:
            raise ValidationError(
                "Only an initiated payment can be marked pending."
            )

        if provider_reference:
            payment.provider_reference = provider_reference.strip()
        payment.status = EcommercePayment.PENDING
        payment.save(
            update_fields=[
                "provider_reference",
                "status",
                "updated_at",
            ]
        )
        return payment, True

    @classmethod
    @transaction.atomic
    def confirm_payment(
        cls,
        *,
        payment,
        provider_reference,
        actor=None,
    ):
        """
        Confirm payment, post the Customer Advance, then confirm and route
        every Enterprise Order created by the checkout.
        """
        if not isinstance(payment, EcommercePayment) or not payment.pk:
            raise ValidationError("A saved Ecommerce payment is required.")

        provider_reference = cls._required(
            provider_reference,
            "provider_reference",
        )

        # Do not use select_related() on this SELECT FOR UPDATE query. Some
        # payment relations are nullable and PostgreSQL cannot lock the
        # nullable side of an outer join.
        payment = EcommercePayment.objects.select_for_update().get(
            pk=payment.pk
        )
        checkout = EcommerceCheckout.objects.select_for_update().get(
            pk=payment.checkout_id
        )
        payment.checkout = checkout

        if payment.status == EcommercePayment.CONFIRMED:
            return payment, False
        if payment.status not in {
            EcommercePayment.INITIATED,
            EcommercePayment.PENDING,
        }:
            raise ValidationError(
                f"Payment cannot be confirmed while it is "
                f"{payment.get_status_display()}."
            )
        if checkout.status in {"CANCELLED", "FAILED"}:
            raise ValidationError(
                f"Checkout {checkout.checkout_number} is not payable."
            )
        if payment.amount != checkout.total_amount:
            raise ValidationError(
                "Payment amount no longer matches the checkout total."
            )

        duplicate_reference = (
            EcommercePayment.objects
            .exclude(pk=payment.pk)
            .filter(
                provider=payment.provider,
                provider_reference=provider_reference,
                status=EcommercePayment.CONFIRMED,
            )
            .exists()
        )
        if duplicate_reference:
            raise ValidationError(
                "This provider payment reference has already been confirmed."
            )

        finance_method = cls.FINANCE_PAYMENT_METHODS[payment.method]
        advance, advance_created = CustomerAdvanceService.receive_advance(
            customer=checkout.user,
            customer_name=checkout.customer_name,
            customer_phone=checkout.customer_phone,
            amount=payment.amount,
            source_type="ECOMMERCE_CHECKOUT",
            source_id=str(checkout.pk),
            source_reference=checkout.checkout_number,
            payment_method=finance_method,
            actor=actor,
        )

        payment.provider_reference = provider_reference
        payment.customer_advance = advance
        payment.status = EcommercePayment.CONFIRMED
        payment.confirmed_by = cls._user(actor)
        payment.confirmed_at = timezone.now()
        payment.failure_reason = ""
        payment.full_clean()
        payment.save(
            update_fields=[
                "provider_reference",
                "customer_advance",
                "status",
                "confirmed_by",
                "confirmed_at",
                "failure_reason",
                "updated_at",
            ]
        )

        order_ids = list(
            checkout.checkout_orders.order_by("pk").values_list(
                "order_id",
                flat=True,
            )
        )
        if not order_ids:
            raise ValidationError(
                "This checkout has no Enterprise Orders to confirm."
            )

        confirmed_orders = []
        for link in checkout.checkout_orders.select_related("order").order_by(
            "pk"
        ):
            order = link.order

            # Payment is confirmed even though Finance keeps it under
            # Customer Advances until the order is delivered.
            if order.payment_status != "PAID":
                order.payment_status = "PAID"
                order.save(
                    update_fields=[
                        "payment_status",
                        "updated_at",
                    ]
                )

            if order.status == "PENDING":
                result = OrderService.confirm(
                    order=order,
                    actor=actor,
                )
                confirmed_orders.append(result or order)

            elif order.status in {
                "CONFIRMED",
                "PROCESSING",
                "READY",
                "DELIVERED",
                "COMPLETED",
            }:
                confirmed_orders.append(order)

            else:
                raise ValidationError(
                    f"Order {order.order_number} cannot be confirmed "
                    f"from status {order.status}."
                )

        cls._dispatch(
            event_code="ECOMMERCE_PAYMENT_CONFIRMED",
            payment=payment,
            actor=actor,
            title="Ecommerce Payment Confirmed",
            message=(
                f"Payment {payment.payment_number} was confirmed; "
                f"{len(confirmed_orders)} Enterprise Order(s) were released."
            ),
            level="SUCCESS",
            metadata={
                "customer_advance_id": advance.pk,
                "customer_advance_created": advance_created,
                "order_ids": order_ids,
            },
        )
        return payment, True

    @classmethod
    @transaction.atomic
    def fail_payment(
        cls,
        *,
        payment,
        reason,
        actor=None,
    ):
        """Close an unconfirmed attempt without changing its checkout."""
        if not isinstance(payment, EcommercePayment) or not payment.pk:
            raise ValidationError("A saved Ecommerce payment is required.")
        reason = cls._required(reason, "reason")

        payment = EcommercePayment.objects.select_for_update().get(
            pk=payment.pk
        )
        if payment.status == EcommercePayment.FAILED:
            return payment, False
        if payment.status not in {
            EcommercePayment.INITIATED,
            EcommercePayment.PENDING,
        }:
            raise ValidationError(
                "Only an unconfirmed payment attempt can be failed."
            )

        payment.status = EcommercePayment.FAILED
        payment.failure_reason = reason
        payment.failed_at = timezone.now()
        payment.full_clean()
        payment.save(
            update_fields=[
                "status",
                "failure_reason",
                "failed_at",
                "updated_at",
            ]
        )

        cls._dispatch(
            event_code="ECOMMERCE_PAYMENT_FAILED",
            payment=payment,
            actor=actor,
            title="Ecommerce Payment Failed",
            message=(
                f"Payment {payment.payment_number} failed: {reason}"
            ),
            level="WARNING",
        )
        return payment, True
