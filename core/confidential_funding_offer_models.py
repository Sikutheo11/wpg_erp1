from decimal import Decimal, ROUND_HALF_UP
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.job_investment_models import JobInvestment


ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")


class ContractorFundingOffer(models.Model):
    """Contractor's private, pre-agreed capital request and return offer.

    The offered return is determined before funding. Settlement must not be
    recalculated from actual project profit.
    """

    STATUSES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("VERIFIED", "Verified"),
        ("MATCHING", "Matching"),
        ("MATCHED", "Matched"),
        ("FUNDED", "Funded"),
        ("CLOSED", "Closed"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    )

    reference = models.CharField(max_length=40, unique=True, blank=True)
    job_investment = models.OneToOneField(
        JobInvestment,
        on_delete=models.PROTECT,
        related_name="confidential_funding_offer",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="DRAFT",
        db_index=True,
    )
    capital_required = models.DecimalField(max_digits=18, decimal_places=2)
    offered_return_percent = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        help_text=(
            "Contractor-agreed return percentage on capital requested. "
            "It is fixed before funding and is not based on actual net profit."
        ),
    )
    expected_duration_days = models.PositiveIntegerField()
    security_available = models.BooleanField(default=False)
    controlled_project_account_accepted = models.BooleanField(default=False)
    contractor_costing_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Private snapshot of contractor estimates used to make the offer. "
            "It is not a settlement formula."
        ),
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_contractor_funding_offers",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_contractor_funding_offers",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ["-created_at"]
        permissions = [
            ("manage_contractor_funding_offer", "Can manage contractor funding offers"),
            ("verify_contractor_funding_offer", "Can verify contractor funding offers"),
            ("view_private_contractor_costing", "Can view private contractor costing"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capital_required__gt=0),
                name="core_contractor_offer_capital_gt_zero",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(offered_return_percent__gte=0)
                    & models.Q(offered_return_percent__lte=100)
                ),
                name="core_contractor_offer_return_0_100",
            ),
        ]

    def clean(self):
        errors = {}
        if self.capital_required is not None and self.capital_required <= 0:
            errors["capital_required"] = "Capital required must be greater than zero."
        if self.offered_return_percent is not None and not (
            ZERO <= self.offered_return_percent <= HUNDRED
        ):
            errors["offered_return_percent"] = "Return percentage must be between 0 and 100."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                f"OFFER-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def agreed_return_amount(self):
        return (
            Decimal(str(self.capital_required or 0))
            * Decimal(str(self.offered_return_percent or 0))
            / HUNDRED
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def total_repayment(self):
        return (
            Decimal(str(self.capital_required or 0))
            + self.agreed_return_amount
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __str__(self):
        return self.reference
