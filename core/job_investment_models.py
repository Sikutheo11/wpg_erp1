from decimal import Decimal, ROUND_HALF_UP
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone


ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")


class JobInvestment(models.Model):
    """
    Funding wrapper for ONE specific customer job/order.

    The Order remains the commercial job.
    Finance remains the owner of actual cash/accounting.
    This model only tracks how that specific job is financed and settled.
    """

    STATUSES = (
        ("DRAFT", "Draft"),
        ("FUNDING", "Funding"),
        ("FUNDED", "Fully funded"),
        ("ACTIVE", "Job in progress"),
        ("SETTLEMENT", "Investor settlement"),
        ("CLOSED", "Closed"),
        ("CANCELLED", "Cancelled"),
    )

    reference = models.CharField(max_length=40, unique=True, blank=True)
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="job_investment",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="DRAFT",
        db_index=True,
    )

    estimated_job_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
        help_text="Approved estimate required to complete this specific job.",
    )
    contract_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
        help_text="Approved customer quotation/contract value for this job.",
    )
    wpg_capital_committed = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
        help_text="WPG's own money committed to this job.",
    )

    actual_revenue_snapshot = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
        editable=False,
        help_text="Finance-synced customer revenue for this job.",
    )
    actual_cost_snapshot = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
        editable=False,
        help_text="Finance-synced actual cost of this job.",
    )

    notes = models.TextField(blank=True)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opened_job_investments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "core"
        ordering = ["-created_at"]
        permissions = [
            ("manage_job_investment", "Can manage job investment"),
            ("approve_investor_agreement", "Can approve investor agreement"),
            ("settle_job_investor", "Can settle job investor"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estimated_job_cost__gte=0),
                name="core_job_inv_est_cost_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(contract_value__gte=0),
                name="core_job_inv_contract_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(wpg_capital_committed__gte=0),
                name="core_job_inv_wpg_capital_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(actual_revenue_snapshot__gte=0),
                name="core_job_inv_revenue_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(actual_cost_snapshot__gte=0),
                name="core_job_inv_cost_nonnegative",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                f"JINV-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def investor_capital_received(self):
        return (
            self.investor_contributions.filter(status="RECEIVED")
            .aggregate(total=Sum("amount"))["total"]
            or ZERO
        )

    @property
    def total_capital_available(self):
        return (
            Decimal(str(self.wpg_capital_committed or 0))
            + Decimal(str(self.investor_capital_received or 0))
        )

    @property
    def funding_gap(self):
        return max(
            Decimal(str(self.estimated_job_cost or 0))
            - self.total_capital_available,
            ZERO,
        )

    @property
    def estimated_profit(self):
        return (
            Decimal(str(self.contract_value or 0))
            - Decimal(str(self.estimated_job_cost or 0))
        )

    @property
    def actual_profit_snapshot(self):
        return (
            Decimal(str(self.actual_revenue_snapshot or 0))
            - Decimal(str(self.actual_cost_snapshot or 0))
        )

    def __str__(self):
        return f"{self.reference} - {self.order}"


class JobInvestorAgreement(models.Model):
    RETURN_MODELS = (
        ("CAPITAL_ONLY", "Return capital only"),
        ("FIXED_PROFIT", "Capital + fixed profit"),
        ("PROFIT_SHARE", "Capital + percentage of actual job profit"),
    )

    STATUSES = (
        ("DRAFT", "Draft"),
        ("APPROVED", "Approved"),
        ("ACTIVE", "Active"),
        ("SETTLEMENT_DUE", "Settlement due"),
        ("SETTLED", "Settled"),
        ("CANCELLED", "Cancelled"),
    )

    job_investment = models.ForeignKey(
        JobInvestment,
        on_delete=models.CASCADE,
        related_name="investor_agreements",
    )
    investor = models.ForeignKey(
        "finance.Counterparty",
        on_delete=models.PROTECT,
        related_name="job_investor_agreements",
        help_text="Use the existing Finance Counterparty identity.",
    )
    agreement_number = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="DRAFT",
        db_index=True,
    )

    committed_capital = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    return_model = models.CharField(
        max_length=20,
        choices=RETURN_MODELS,
        default="CAPITAL_ONLY",
    )
    fixed_profit_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
    )
    profit_share_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=ZERO,
        help_text="Percentage of positive ACTUAL profit of this job.",
    )

    agreement_date = models.DateField(default=timezone.localdate)
    repayment_due_date = models.DateField(null=True, blank=True)
    terms = models.TextField(blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_job_investor_agreements",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_job_investor_agreements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ["job_investment", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(committed_capital__gt=0),
                name="core_job_agreement_capital_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(fixed_profit_amount__gte=0),
                name="core_job_agreement_fixed_profit_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(profit_share_percent__gte=0)
                    & models.Q(profit_share_percent__lte=100)
                ),
                name="core_job_agreement_profit_share_0_100",
            ),
            models.UniqueConstraint(
                fields=["job_investment", "investor"],
                name="core_unique_investor_per_job",
            ),
        ]

    def clean(self):
        errors = {}

        if self.committed_capital is not None and self.committed_capital <= 0:
            errors["committed_capital"] = "Committed capital must be greater than zero."

        if self.return_model == "FIXED_PROFIT":
            if self.fixed_profit_amount is None or self.fixed_profit_amount <= 0:
                errors["fixed_profit_amount"] = "Enter the agreed fixed profit."
        elif self.fixed_profit_amount:
            errors["fixed_profit_amount"] = (
                "Fixed profit is only used with the Fixed Profit return model."
            )

        if self.return_model == "PROFIT_SHARE":
            if (
                self.profit_share_percent is None
                or self.profit_share_percent <= 0
                or self.profit_share_percent > 100
            ):
                errors["profit_share_percent"] = (
                    "Profit share must be above 0 and not exceed 100%."
                )
        elif self.profit_share_percent:
            errors["profit_share_percent"] = (
                "Profit share is only used with the Profit Share return model."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.agreement_number:
            self.agreement_number = (
                f"JAGR-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def capital_received(self):
        return (
            self.contributions.filter(status="RECEIVED")
            .aggregate(total=Sum("amount"))["total"]
            or ZERO
        )

    @property
    def remaining_commitment(self):
        return max(
            Decimal(str(self.committed_capital or 0))
            - Decimal(str(self.capital_received or 0)),
            ZERO,
        )

    def calculate_investor_profit(self, actual_job_profit=None):
        if self.return_model == "CAPITAL_ONLY":
            return ZERO

        if self.return_model == "FIXED_PROFIT":
            return Decimal(str(self.fixed_profit_amount or 0)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        profit = (
            Decimal(str(actual_job_profit))
            if actual_job_profit is not None
            else self.job_investment.actual_profit_snapshot
        )
        positive_profit = max(profit, ZERO)

        return (
            positive_profit
            * Decimal(str(self.profit_share_percent or 0))
            / HUNDRED
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    def __str__(self):
        return f"{self.agreement_number} - {self.investor}"


class JobInvestorContribution(models.Model):
    STATUSES = (
        ("PLEDGED", "Pledged"),
        ("RECEIVED", "Received"),
        ("REVERSED", "Reversed"),
    )

    agreement = models.ForeignKey(
        JobInvestorAgreement,
        on_delete=models.CASCADE,
        related_name="contributions",
    )
    job_investment = models.ForeignKey(
        JobInvestment,
        on_delete=models.CASCADE,
        related_name="investor_contributions",
        editable=False,
    )
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="PLEDGED",
        db_index=True,
    )
    received_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)

    finance_income_declaration = models.OneToOneField(
        "finance.IncomeDeclaration",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="job_investor_contribution",
        help_text=(
            "When cash is actually received, link the confirmed Finance "
            "Income Declaration instead of creating another cash transaction."
        ),
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_job_investor_contributions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="core_job_contribution_amount_gt_zero",
            ),
        ]

    def clean(self):
        errors = {}

        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "Contribution must be greater than zero."

        if self.agreement_id:
            self.job_investment = self.agreement.job_investment

            existing_received = (
                self.agreement.contributions.filter(status="RECEIVED")
                .exclude(pk=self.pk)
                .aggregate(total=Sum("amount"))["total"]
                or ZERO
            )
            if (
                self.status == "RECEIVED"
                and existing_received + Decimal(str(self.amount or 0))
                > self.agreement.committed_capital
            ):
                errors["amount"] = (
                    "Received investor capital cannot exceed the agreement commitment."
                )

        if self.status == "RECEIVED" and not self.received_date:
            errors["received_date"] = "Received date is required."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.agreement_id:
            self.job_investment = self.agreement.job_investment
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.agreement.agreement_number} - {self.amount}"


class JobInvestorSettlement(models.Model):
    STATUSES = (
        ("DRAFT", "Draft"),
        ("APPROVED", "Approved"),
        ("PARTIAL", "Partially paid"),
        ("SETTLED", "Settled"),
        ("CANCELLED", "Cancelled"),
    )

    agreement = models.OneToOneField(
        JobInvestorAgreement,
        on_delete=models.PROTECT,
        related_name="settlement",
    )
    principal_due = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
    )
    investor_profit_due = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
    )
    total_due = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
        editable=False,
    )
    amount_paid = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=ZERO,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="DRAFT",
        db_index=True,
    )

    finance_debt_record = models.OneToOneField(
        "finance.DebtRecord",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="job_investor_settlement",
        help_text=(
            "Repayment/payment execution remains in Finance. "
            "Link its debt/payable record here."
        ),
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_job_investor_settlements",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "core"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(principal_due__gte=0),
                name="core_job_settlement_principal_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(investor_profit_due__gte=0),
                name="core_job_settlement_profit_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(amount_paid__gte=0),
                name="core_job_settlement_paid_nonnegative",
            ),
        ]

    def save(self, *args, **kwargs):
        self.total_due = (
            Decimal(str(self.principal_due or 0))
            + Decimal(str(self.investor_profit_due or 0))
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        if self.total_due > 0 and self.amount_paid >= self.total_due:
            self.status = "SETTLED"
            if not self.settled_at:
                self.settled_at = timezone.now()
        elif self.amount_paid > 0:
            self.status = "PARTIAL"

        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def balance_due(self):
        return max(
            Decimal(str(self.total_due or 0))
            - Decimal(str(self.amount_paid or 0)),
            ZERO,
        )

    def __str__(self):
        return f"Settlement - {self.agreement.agreement_number}"
