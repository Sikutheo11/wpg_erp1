from decimal import Decimal
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.job_investment_models import JobInvestment


ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")


class CapitalProviderMandate(models.Model):
    """Private conditions supplied by a verified capital provider.

    The contractor never browses this record directly. Matching is performed
    internally and only anonymous opportunity information may be disclosed.
    """

    STATUSES = (
        ("DRAFT", "Draft"),
        ("ACTIVE", "Active"),
        ("PAUSED", "Paused"),
        ("CLOSED", "Closed"),
    )
    RISK_LEVELS = (
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    )

    reference = models.CharField(max_length=40, unique=True, blank=True)
    capital_provider = models.ForeignKey(
        "finance.Counterparty",
        on_delete=models.PROTECT,
        related_name="capital_provider_mandates",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="DRAFT",
        db_index=True,
    )
    minimum_capital = models.DecimalField(max_digits=18, decimal_places=2)
    maximum_capital = models.DecimalField(max_digits=18, decimal_places=2)
    minimum_return_percent = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=ZERO,
        help_text="Minimum contractor-agreed return on capital; not actual job profit.",
    )
    maximum_duration_days = models.PositiveIntegerField()
    preferred_business_units = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional list of business-unit codes accepted by the provider.",
    )
    risk_tolerance = models.CharField(
        max_length=10,
        choices=RISK_LEVELS,
        default="MEDIUM",
    )
    requires_controlled_project_account = models.BooleanField(default=False)
    requires_security = models.BooleanField(default=False)
    private_conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Internal matching conditions. Never expose directly to contractors.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_capital_provider_mandates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ["-created_at"]
        permissions = [
            ("view_private_capital_provider", "Can view private capital provider details"),
            ("manage_capital_provider_mandate", "Can manage capital provider mandates"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(minimum_capital__gt=0),
                name="core_cap_mandate_min_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(maximum_capital__gt=0),
                name="core_cap_mandate_max_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(minimum_return_percent__gte=0),
                name="core_cap_mandate_return_nonnegative",
            ),
        ]

    def clean(self):
        errors = {}
        if self.minimum_capital is not None and self.maximum_capital is not None:
            if self.minimum_capital > self.maximum_capital:
                errors["maximum_capital"] = (
                    "Maximum capital must be greater than or equal to minimum capital."
                )
        if self.minimum_return_percent is not None and self.minimum_return_percent < 0:
            errors["minimum_return_percent"] = "Minimum return cannot be negative."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                f"CPM-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.reference


class FundingMatch(models.Model):
    """Internal double-blind match between one job and one provider mandate."""

    STATUSES = (
        ("CANDIDATE", "Candidate"),
        ("ADMIN_REVIEW", "Admin review"),
        ("PROVIDER_INTERESTED", "Provider interested"),
        ("CONTRACTOR_INTERESTED", "Contractor interested"),
        ("TERMS", "Terms discussion"),
        ("APPROVED", "Approved"),
        ("DECLINED", "Declined"),
        ("EXPIRED", "Expired"),
    )

    reference = models.CharField(max_length=40, unique=True, blank=True)
    job_investment = models.ForeignKey(
        JobInvestment,
        on_delete=models.CASCADE,
        related_name="confidential_matches",
    )
    mandate = models.ForeignKey(
        CapitalProviderMandate,
        on_delete=models.PROTECT,
        related_name="funding_matches",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUSES,
        default="CANDIDATE",
        db_index=True,
    )
    match_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=ZERO,
        editable=False,
    )
    score_breakdown = models.JSONField(default=dict, blank=True, editable=False)
    anonymous_opportunity_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Only sanitized, non-identifying deal information belongs here.",
    )
    provider_identity_disclosed = models.BooleanField(default=False)
    contractor_identity_disclosed = models.BooleanField(default=False)
    disclosure_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_capital_match_disclosures",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_funding_matches",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ["-match_score", "-created_at"]
        permissions = [
            ("manage_confidential_matching", "Can manage confidential funding matches"),
            ("approve_identity_disclosure", "Can approve identity disclosure for a match"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["job_investment", "mandate"],
                name="core_unique_job_capital_mandate_match",
            ),
            models.CheckConstraint(
                condition=(models.Q(match_score__gte=0) & models.Q(match_score__lte=100)),
                name="core_funding_match_score_0_100",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                f"MATCH-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.reference


class ProjectAccountControl(models.Model):
    """Limited control metadata for a dedicated project bank account.

    This model records the agreed bank mandate. It does not itself move money
    and must never store online-banking passwords, PINs, OTPs or secret keys.
    """

    STATUSES = (
        ("PROPOSED", "Proposed"),
        ("BANK_REVIEW", "Bank review"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("CLOSED", "Closed"),
    )
    SIGNING_RULES = (
        ("CONTRACTOR_ONLY", "Contractor only"),
        ("JOINT", "Contractor + platform jointly"),
        ("MAKER_CHECKER", "Maker/checker authorization"),
        ("BANK_CONTROLLED", "Bank-controlled settlement instructions"),
    )

    job_investment = models.OneToOneField(
        JobInvestment,
        on_delete=models.PROTECT,
        related_name="project_account_control",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="PROPOSED",
        db_index=True,
    )
    bank_name = models.CharField(max_length=150)
    account_name = models.CharField(max_length=180)
    masked_account_number = models.CharField(
        max_length=80,
        help_text="Store a masked/tokenized account reference, not unnecessary bank secrets.",
    )
    signing_rule = models.CharField(
        max_length=30,
        choices=SIGNING_RULES,
        default="JOINT",
    )
    platform_approval_required = models.BooleanField(default=True)
    transaction_approval_threshold = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
        help_text="Payments at or above this amount require the agreed second authorization.",
    )
    client_payment_directed_here = models.BooleanField(default=False)
    bank_mandate_reference = models.CharField(max_length=100, blank=True)
    bank_confirmed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_account_controls",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ["-created_at"]
        permissions = [
            ("manage_project_account_control", "Can manage project account controls"),
            ("view_project_bank_details", "Can view controlled project bank details"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(transaction_approval_threshold__gte=0),
                name="core_project_account_threshold_nonnegative",
            ),
        ]

    def clean(self):
        errors = {}
        if self.platform_approval_required and self.signing_rule == "CONTRACTOR_ONLY":
            errors["signing_rule"] = (
                "Contractor-only signing cannot require platform approval."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_investment.reference} - {self.bank_name}"
