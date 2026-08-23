import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class EcommercePayment(models.Model):
    """
    A payment attempt for one Ecommerce checkout.

    Multiple failed or abandoned attempts may belong to a checkout, but the
    database permits only one CONFIRMED payment. A confirmed payment is linked
    to the CustomerAdvance created in Finance.
    """

    CASH = "CASH"
    BANK = "BANK"
    MOBILE_MONEY = "MOBILE_MONEY"
    CARD = "CARD"
    EKASH = "EKASH"

    METHODS = (
        (CASH, "Cash"),
        (BANK, "Bank Transfer"),
        (MOBILE_MONEY, "Mobile Money"),
        (CARD, "Visa / Mastercard"),
        (EKASH, "eKash"),
    )

    INITIATED = "INITIATED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

    STATUSES = (
        (INITIATED, "Initiated"),
        (PENDING, "Awaiting Confirmation"),
        (CONFIRMED, "Confirmed"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
        (REFUNDED, "Refunded"),
    )

    payment_number = models.CharField(
        max_length=60,
        unique=True,
        blank=True,
    )
    checkout = models.ForeignKey(
        "ecommerce.EcommerceCheckout",
        on_delete=models.PROTECT,
        related_name="payments",
    )
    method = models.CharField(
        max_length=30,
        choices=METHODS,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default=INITIATED,
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3, default="RWF")

    # The PSP may be MTN MoMo, Airtel Money, a bank, Flutterwave, etc.
    provider = models.CharField(max_length=80, blank=True)
    provider_reference = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
    )

    provider_request_id = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
        help_text=(
            "Transaction/request identifier assigned when the "
            "payment is sent to the payment provider."
        ),
    )

    provider_status = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Latest raw status returned by the payment provider.",
    )

    provider_response = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Latest non-sensitive provider response used for "
            "payment reconciliation and audit."
        ),
    )

    last_status_check_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    callback_received_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    customer_reference = models.CharField(
        max_length=120,
        blank=True,
        help_text="Phone number, bank reference or customer-facing receipt.",
    )
    idempotency_key = models.CharField(
        max_length=180,
        unique=True,
        null=True,
        blank=True,
        help_text="Prevents a provider callback from being processed twice.",
    )
    proof_image = models.ImageField(
        upload_to="ecommerce/payment_proofs/",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)

    customer_advance = models.OneToOneField(
        "finance.CustomerAdvance",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ecommerce_payment",
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_ecommerce_payments",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_ecommerce_payments",
    )
    initiated_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-initiated_at", "-pk"]
        permissions = [
            (
                "confirm_ecommercepayment",
                "Can confirm ecommerce payments",
            ),
            (
                "refund_ecommercepayment",
                "Can refund ecommerce payments",
            ),
        ]
        indexes = [
            models.Index(
                fields=["checkout", "status"],
                name="ecom_pay_checkout_status_idx",
            ),
            models.Index(
                fields=["provider", "provider_reference"],
                name="ecom_pay_provider_ref_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="ecom_payment_amount_positive",
            ),
            models.UniqueConstraint(
                fields=["checkout"],
                condition=Q(status="CONFIRMED"),
                name="ecom_one_confirmed_payment_per_checkout",
            ),
        ]

    def clean(self):
        super().clean()

        if self.checkout_id:
            expected_amount = self.checkout.total_amount
            if self.amount != expected_amount:
                raise ValidationError(
                    {
                        "amount": (
                            "Ecommerce requires full payment. "
                            f"The checkout total is {expected_amount} "
                            f"{self.checkout.currency}."
                        )
                    }
                )

            if self.currency != self.checkout.currency:
                raise ValidationError(
                    {
                        "currency": (
                            "Payment currency must match checkout currency."
                        )
                    }
                )

        if self.status == self.CONFIRMED:
            if self.confirmed_at is None:
                raise ValidationError(
                    {
                        "confirmed_at": (
                            "A confirmed payment needs confirmation time."
                        )
                    }
                )
            if self.customer_advance_id is None:
                raise ValidationError(
                    {
                        "customer_advance": (
                            "A confirmed payment must have a Finance "
                            "customer advance."
                        )
                    }
                )

        if self.status == self.FAILED and not self.failure_reason.strip():
            raise ValidationError(
                {
                    "failure_reason": (
                        "Explain why this payment attempt failed."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = (
                f"EPAY-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )

        self.currency = (self.currency or "RWF").upper()
        self.provider = (self.provider or "").strip()
        self.provider_reference = (
            self.provider_reference or ""
        ).strip()
        self.customer_reference = (
            self.customer_reference or ""
        ).strip()
        self.idempotency_key = (
            (self.idempotency_key or "").strip() or None
        )

        super().save(*args, **kwargs)

    @property
    def is_confirmed(self):
        return self.status == self.CONFIRMED

    def __str__(self):
        return (
            f"{self.payment_number} — "
            f"{self.checkout.checkout_number} — "
            f"{self.get_status_display()}"
        )

class PaymentProviderConfiguration(models.Model):
    """
    Maps an Ecommerce payment provider to the Finance account where
    WPG receives or settles the money.

    API credentials are never stored here. They belong in environment
    variables / deployment secrets.
    """

    MTN_MOMO = "MTN_MOMO"
    AIRTEL_MONEY = "AIRTEL_MONEY"
    RSWITCH_CARD = "RSWITCH_CARD"
    EKASH = "EKASH"

    PROVIDERS = (
        (MTN_MOMO, "MTN MoMo"),
        (AIRTEL_MONEY, "Airtel Money"),
        (RSWITCH_CARD, "Visa / Mastercard via RSwitch"),
        (EKASH, "eKash / RNDPS"),
    )

    provider = models.CharField(
        max_length=40,
        choices=PROVIDERS,
        unique=True,
    )

    settlement_account = models.ForeignKey(
        "finance.Account",
        on_delete=models.PROTECT,
        related_name="ecommerce_payment_providers",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    sort_order = models.PositiveSmallIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "sort_order",
            "provider",
        ]

    def clean(self):
        super().clean()

        if not self.settlement_account_id:
            return

        required_account_type = {
            self.MTN_MOMO: "mobile",
            self.AIRTEL_MONEY: "mobile",
            self.RSWITCH_CARD: "bank",
            self.EKASH: "bank",
        }.get(self.provider)

        if (
            required_account_type
            and self.settlement_account.account_type
            != required_account_type
        ):
            raise ValidationError(
                {
                    "settlement_account": (
                        f"{self.get_provider_display()} requires "
                        f"a Finance {required_account_type} account."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.get_provider_display()} → "
            f"{self.settlement_account.name}"
        )
