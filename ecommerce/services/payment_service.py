from django.core.exceptions import (
    ImproperlyConfigured,
    ValidationError,
)
from django.db import transaction
from django.utils import timezone
from core.event_engine import EventEngine
from finance.services.customer_advance_service import (
    CustomerAdvanceService,
)
from orders.services import OrderService
from ..gateways import PaymentGatewayRegistry
from .payment_provider_service import (
    PaymentProviderConfigurationService,
)
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
        EcommercePayment.CARD: "bank",
        EcommercePayment.EKASH: "bank",
    }

    AUTOMATED_PROVIDERS = {
        "MTN_MOMO",
        "AIRTEL_MONEY",
        "RSWITCH_CARD",
        "EKASH",
    }

    @classmethod
    def is_automated_provider(cls, provider):
        return (
            str(provider or "").strip().upper()
            in cls.AUTOMATED_PROVIDERS
        )

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

        idempotency_key = (
            idempotency_key or ""
        ).strip() or None

        # Lock the checkout first so concurrent attempts for the same checkout
        # are serialized.
        checkout = EcommerceCheckout.objects.select_for_update().get(
            pk=checkout.pk
        )

        if checkout.status in {
            "CANCELLED",
            "FAILED",
            "COMPLETED",
        }:
            raise ValidationError(
                f"Checkout {checkout.checkout_number} cannot accept payment "
                f"while it is {checkout.get_status_display()}."
            )

        if checkout.total_amount <= 0:
            raise ValidationError(
                "Checkout total must be greater than zero."
            )

        if checkout.payments.filter(
            status=EcommercePayment.CONFIRMED
        ).exists():
            raise ValidationError(
                "This checkout has already been paid."
            )

        if idempotency_key:
            existing = (
                EcommercePayment.objects
                .select_for_update()
                .filter(
                    idempotency_key=idempotency_key
                )
                .first()
            )

            if existing is not None:
                if existing.checkout_id != checkout.pk:
                    raise ValidationError(
                        "This idempotency key belongs to another checkout."
                    )

                if existing.status in {
                    EcommercePayment.INITIATED,
                    EcommercePayment.PENDING,
                    EcommercePayment.CONFIRMED,
                }:
                    return existing, False

                if existing.status in {
                    EcommercePayment.FAILED,
                    EcommercePayment.CANCELLED,
                }:
                    # Preserve the old payment audit record but release this
                    # client-attempt key for the new retry.
                    existing.idempotency_key = None
                    existing.save(
                        update_fields=[
                            "idempotency_key",
                            "updated_at",
                        ]
                    )

                else:
                    raise ValidationError(
                        "This payment attempt cannot be retried."
                    )

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
        provider_request_id="",
        provider_status="",
        provider_response=None,
        actor=None,
    ):
        """Mark a provider request as sent and awaiting confirmation."""
        if not isinstance(payment, EcommercePayment) or not payment.pk:
            raise ValidationError(
                "A saved Ecommerce payment is required."
            )

        payment = (
            EcommercePayment.objects
            .select_for_update()
            .get(pk=payment.pk)
        )

        if payment.status == EcommercePayment.PENDING:
            return payment, False

        if payment.status != EcommercePayment.INITIATED:
            raise ValidationError(
                "Only an initiated payment can be marked pending."
            )

        if provider_reference:
            payment.provider_reference = (
                provider_reference.strip()
            )

        payment.provider_request_id = (
            provider_request_id or ""
        ).strip()

        payment.provider_status = (
            provider_status or "PENDING"
        ).strip().upper()

        payment.provider_response = (
            provider_response
            if isinstance(provider_response, dict)
            else {}
        )

        payment.status = EcommercePayment.PENDING

        payment.save(
            update_fields=[
                "provider_reference",
                "provider_request_id",
                "provider_status",
                "provider_response",
                "status",
                "updated_at",
            ]
        )

        return payment, True


    @classmethod
    def request_provider_payment(
        cls,
        *,
        payment,
        callback_url="",
        actor=None,
    ):
        """
        Send an initiated payment to its external payment gateway.

        The external HTTP call deliberately runs outside a database
        transaction. Finance is not posted at this stage.
        """
        if not isinstance(payment, EcommercePayment) or not payment.pk:
            raise ValidationError(
                "A saved Ecommerce payment is required."
            )

        payment = (
            EcommercePayment.objects
            .select_related("checkout")
            .get(pk=payment.pk)
        )

        if (
            payment.status == EcommercePayment.PENDING
            and payment.provider_request_id
        ):
            return payment, False

        if payment.status != EcommercePayment.INITIATED:
            raise ValidationError(
                "Only an initiated payment can be sent "
                "to a payment provider."
            )

        # Ensure WPG has a valid Finance settlement destination.
        PaymentProviderConfigurationService.get_settlement_account(
            payment.provider
        )

        try:
            gateway = PaymentGatewayRegistry.get(
                payment.provider
            )
        except ImproperlyConfigured as error:
            raise ValidationError(
                {
                    "provider": (
                        f"{payment.provider} payment gateway "
                        "is not available."
                    )
                }
            ) from error

        try:
            result = gateway.initiate_payment(
                amount=payment.amount,
                currency=payment.currency,
                customer_reference=(
                    payment.customer_reference
                ),
                merchant_reference=payment.payment_number,
                callback_url=callback_url,
            )
        except Exception as error:
            # Do not expose provider credentials or raw transport
            # errors to the customer.
            raise ValidationError(
                {
                    "provider": (
                        "The payment provider could not be "
                        "reached. Please try again."
                    )
                }
            ) from error

        if not result.successful:
            payment.provider_request_id = (
                result.provider_request_id
            )
            payment.provider_status = (
                result.provider_status
            )
            payment.provider_response = (
                result.raw_response
            )
            payment.save(
                update_fields=[
                    "provider_request_id",
                    "provider_status",
                    "provider_response",
                    "updated_at",
                ]
            )

            cls.fail_payment(
                payment=payment,
                reason=(
                    result.message
                    or "Payment provider rejected the request."
                ),
                actor=actor,
            )

            raise ValidationError(
                {
                    "provider": (
                        result.message
                        or "The payment request was rejected."
                    )
                }
            )

        return cls.mark_pending(
            payment=payment,
            provider_request_id=(
                result.provider_request_id
            ),
            provider_reference=(
                result.provider_reference
            ),
            provider_status=(
                result.provider_status
            ),
            provider_response=(
                result.raw_response
            ),
            actor=actor,
        )

    @classmethod
    def check_provider_status(
        cls,
        *,
        payment,
        actor=None,
    ):
        """
        Ask the external gateway for the current payment status.

        PENDING      -> leave payment pending
        SUCCESSFUL   -> confirm Ecommerce payment and Finance
        FAILED       -> mark payment failed
        """
        if not isinstance(payment, EcommercePayment) or not payment.pk:
            raise ValidationError(
                "A saved Ecommerce payment is required."
            )

        payment = EcommercePayment.objects.select_related(
            "checkout",
            "customer_advance",
        ).get(pk=payment.pk)

        if payment.status == EcommercePayment.CONFIRMED:
            return payment, False

        if payment.status in {
            EcommercePayment.FAILED,
            EcommercePayment.CANCELLED,
            EcommercePayment.REFUNDED,
        }:
            return payment, False

        if payment.status != EcommercePayment.PENDING:
            raise ValidationError(
                "Only a pending payment can have its provider status checked."
            )

        if not payment.provider_request_id:
            raise ValidationError(
                "This payment does not have a provider request ID."
            )

        try:
            gateway = PaymentGatewayRegistry.get(
                payment.provider
            )

            result = gateway.get_payment_status(
                provider_request_id=payment.provider_request_id,
            )

        except ImproperlyConfigured as error:
            raise ValidationError(str(error)) from error

        except Exception as error:
            raise ValidationError(
                "The payment provider could not be reached. "
                "Please try again shortly."
            ) from error

        provider_status = (
            result.provider_status or ""
        ).strip().upper()

        payment.provider_status = provider_status
        payment.provider_response = (
            result.raw_response
            if isinstance(result.raw_response, dict)
            else {}
        )
        payment.last_status_check_at = timezone.now()

        if result.provider_reference:
            payment.provider_reference = (
                result.provider_reference
            )

        payment.save(
            update_fields=[
                "provider_status",
                "provider_response",
                "provider_reference",
                "last_status_check_at",
                "updated_at",
            ]
        )

        if provider_status == "PENDING":
            return payment, False

        if provider_status == "SUCCESSFUL":
            provider_reference = (
                result.provider_reference
                or payment.provider_reference
            )

            if not provider_reference:
                raise ValidationError(
                    "The provider reported a successful payment "
                    "without a transaction reference."
                )

            return cls.confirm_payment(
                payment=payment,
                provider_reference=provider_reference,
                actor=actor,
            )

        if provider_status == "FAILED":
            reason = (
                result.message
                or "The payment provider reported that the payment failed."
            )

            return cls.fail_payment(
                payment=payment,
                reason=reason,
                actor=actor,
            )

        # Unknown provider status is deliberately not treated as paid or failed.
        return payment, False

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

        if cls.is_automated_provider(payment.provider):
            if (
                payment.provider_status != "SUCCESSFUL"
                or not payment.provider_request_id
                or not payment.provider_reference
            ):
                raise ValidationError(
                    (
                        f"{payment.provider} payment cannot be "
                        "confirmed manually. A successful response "
                        "from the payment provider is required."
                    )
                )

            if provider_reference != payment.provider_reference:
                raise ValidationError(
                    (
                        "The confirmation reference must match "
                        "the verified provider transaction reference."
                    )
                )
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

    @classmethod
    @transaction.atomic
    def cancel_payment(
        cls,
        *,
        payment,
        reason,
        actor=None,
    ):
        """
        Cancel an unconfirmed Ecommerce payment attempt.

        A confirmed payment cannot be cancelled here because it requires
        a Finance refund and Customer Advance reversal.
        """
        if not isinstance(payment, EcommercePayment) or not payment.pk:
            raise ValidationError(
                "A saved Ecommerce payment is required."
            )

        reason = cls._required(
            reason,
            "reason",
        )

        payment = (
            EcommercePayment.objects
            .select_for_update()
            .get(pk=payment.pk)
        )

        if payment.status == EcommercePayment.CANCELLED:
            return payment, False

        if payment.status == EcommercePayment.CONFIRMED:
            raise ValidationError(
                (
                    f"Confirmed payment {payment.payment_number} "
                    "cannot be cancelled without a Finance refund."
                )
            )

        if payment.status in {
            EcommercePayment.FAILED,
            EcommercePayment.REFUNDED,
        }:
            raise ValidationError(
                (
                    f"Payment {payment.payment_number} cannot be "
                    f"cancelled while it is "
                    f"{payment.get_status_display()}."
                )
            )

        if payment.status not in {
            EcommercePayment.INITIATED,
            EcommercePayment.PENDING,
        }:
            raise ValidationError(
                "Only an unconfirmed payment attempt can be cancelled."
            )

        payment.status = EcommercePayment.CANCELLED
        payment.failure_reason = reason
        payment.full_clean()
        payment.save(
            update_fields=[
                "status",
                "failure_reason",
                "updated_at",
            ]
        )

        cls._dispatch(
            event_code="ECOMMERCE_PAYMENT_CANCELLED",
            payment=payment,
            actor=actor,
            title="Ecommerce Payment Cancelled",
            message=(
                f"Payment {payment.payment_number} was cancelled: "
                f"{reason}"
            ),
            level="WARNING",
        )

        return payment, True

    @classmethod
    @transaction.atomic
    def refund_payment(
        cls,
        *,
        payment,
        reason,
        actor=None,
    ):
        """
        Fully refund one confirmed Ecommerce checkout payment.

        Ecommerce currently requires full checkout payment, therefore
        refunds here are also full-checkout refunds.

        Delivered/completed orders must use a separate return/reversal
        workflow because revenue and inventory may already be posted.
        """
        if not isinstance(payment, EcommercePayment) or not payment.pk:
            raise ValidationError(
                "A saved Ecommerce payment is required."
            )

        reason = cls._required(
            reason,
            "reason",
        )

        payment = (
            EcommercePayment.objects
            .select_for_update()
            .get(pk=payment.pk)
        )

        checkout = (
            EcommerceCheckout.objects
            .select_for_update()
            .get(pk=payment.checkout_id)
        )

        if payment.status == EcommercePayment.REFUNDED:
            return payment, None, False

        if payment.status != EcommercePayment.CONFIRMED:
            raise ValidationError(
                (
                    f"Only a confirmed Ecommerce payment can be "
                    f"refunded. Payment {payment.payment_number} "
                    f"is {payment.get_status_display()}."
                )
            )

        if payment.customer_advance_id is None:
            raise ValidationError(
                (
                    f"Payment {payment.payment_number} has no "
                    "Customer Advance to refund."
                )
            )

        order_links = list(
            checkout.checkout_orders
            .select_related("order")
            .order_by("pk")
        )

        if not order_links:
            raise ValidationError(
                "This checkout has no Enterprise Orders."
            )

        fulfilled_orders = [
            link.order.order_number
            for link in order_links
            if link.order.status in {
                "DELIVERED",
                "COMPLETED",
            }
        ]

        if fulfilled_orders:
            raise ValidationError(
                (
                    "This payment cannot use the pre-delivery refund "
                    "workflow because these orders are already fulfilled: "
                    + ", ".join(fulfilled_orders)
                )
            )

        from ecommerce.models import MarketplaceOrderLine

        protected_marketplace_lines = (
            MarketplaceOrderLine.objects
            .filter(
                order_item__order__ecommerce_checkout_link__checkout=checkout,
                settlement_status__in={
                    "IN_SETTLEMENT",
                    "SETTLED",
                },
            )
            .exists()
        )

        if protected_marketplace_lines:
            raise ValidationError(
                (
                    "This checkout contains Marketplace lines already "
                    "included in or paid through a seller settlement."
                )
            )

        from finance.services import CustomerAdvanceService

        advance = payment.customer_advance

        if payment.amount > advance.available_amount:
            raise ValidationError(
                (
                    f"Only {advance.available_amount} "
                    f"{advance.currency} remains refundable from "
                    f"advance {advance.reference}. "
                    "Use the post-delivery reversal workflow instead."
                )
            )

        refund_entry, refund_created = (
            CustomerAdvanceService.refund_advance(
                advance=advance,
                amount=payment.amount,
                source_id=(
                    f"ECOMMERCE_PAYMENT:{payment.pk}"
                ),
                reason=reason,
                actor=actor,
            )
        )

        payment.status = EcommercePayment.REFUNDED
        payment.refunded_at = timezone.now()
        payment.failure_reason = reason

        payment.full_clean()

        payment.save(
            update_fields=[
                "status",
                "refunded_at",
                "failure_reason",
                "updated_at",
            ]
        )

        for link in order_links:
            order = link.order

            if order.payment_status != "REFUNDED":
                order.payment_status = "REFUNDED"
                order.save(
                    update_fields=[
                        "payment_status",
                        "updated_at",
                    ]
                )

        cls._dispatch(
            event_code="ECOMMERCE_PAYMENT_REFUNDED",
            payment=payment,
            actor=actor,
            title="Ecommerce Payment Refunded",
            message=(
                f"Payment {payment.payment_number} for checkout "
                f"{checkout.checkout_number} was fully refunded."
            ),
            level="WARNING",
            metadata={
                "refund_journal_entry_id": refund_entry.pk,
                "customer_advance_id": payment.customer_advance_id,
                "amount": str(payment.amount),
                "reason": reason,
                "order_ids": [
                    link.order_id
                    for link in order_links
                ],
            },
        )

        return payment, refund_entry, refund_created
