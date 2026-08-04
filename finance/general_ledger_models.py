import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


BUSINESS_UNITS = (
    ("", "Shared / Enterprise"),
    ("FURNITURE", "Furniture & Manufacturing"),
    ("CONSTRUCTION", "Construction & Built Environment"),
    ("AGRICULTURE", "Agriculture / Poultry"),
    ("MARKETPLACE", "Marketplace"),
)


class LedgerAccount(models.Model):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"

    ACCOUNT_TYPES = (
        (ASSET, "Asset"),
        (LIABILITY, "Liability"),
        (EQUITY, "Equity"),
        (REVENUE, "Revenue"),
        (EXPENSE, "Expense"),
    )

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

    NORMAL_BALANCES = (
        (DEBIT, "Debit"),
        (CREDIT, "Credit"),
    )

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES,
        db_index=True,
    )
    normal_balance = models.CharField(
        max_length=10,
        choices=NORMAL_BALANCES,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    business_unit = models.CharField(
        max_length=30,
        choices=BUSINESS_UNITS,
        blank=True,
        db_index=True,
    )
    currency = models.CharField(max_length=3, default="RWF")
    is_control_account = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(
                fields=["account_type", "business_unit", "is_active"],
                name="fin_gl_acct_type_unit_idx",
            ),
        ]

    def clean(self):
        super().clean()

        expected_balance = {
            self.ASSET: self.DEBIT,
            self.EXPENSE: self.DEBIT,
            self.LIABILITY: self.CREDIT,
            self.EQUITY: self.CREDIT,
            self.REVENUE: self.CREDIT,
        }.get(self.account_type)

        if expected_balance and self.normal_balance != expected_balance:
            raise ValidationError(
                {
                    "normal_balance": (
                        f"{self.get_account_type_display()} accounts "
                        f"normally carry a {expected_balance.lower()} balance."
                    )
                }
            )

        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError(
                {"parent": "An account cannot be its own parent."}
            )

    def __str__(self):
        return f"{self.code} — {self.name}"


class JournalEntry(models.Model):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"

    STATUSES = (
        (DRAFT, "Draft"),
        (POSTED, "Posted"),
        (REVERSED, "Reversed"),
    )

    entry_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
    )
    entry_date = models.DateField(default=timezone.localdate, db_index=True)
    description = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default=DRAFT,
        db_index=True,
    )
    business_unit = models.CharField(
        max_length=30,
        choices=BUSINESS_UNITS,
        blank=True,
        db_index=True,
    )
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.CharField(max_length=100, blank=True)
    source_reference = models.CharField(max_length=120, blank=True)
    source_key = models.CharField(
        max_length=180,
        unique=True,
        null=True,
        blank=True,
        help_text="Idempotency key for the business event being posted.",
    )
    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal_entry",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_journal_entries",
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_journal_entries",
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_date", "-pk"]
        indexes = [
            models.Index(
                fields=["status", "entry_date"],
                name="fin_gl_entry_status_date_idx",
            ),
            models.Index(
                fields=["source_type", "source_id"],
                name="fin_gl_entry_source_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.entry_number:
            self.entry_number = (
                f"JE-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )
        if self.source_key == "":
            self.source_key = None
        super().save(*args, **kwargs)

    @property
    def total_debit(self):
        return sum(
            (line.debit for line in self.lines.all()),
            Decimal("0.00"),
        )

    @property
    def total_credit(self):
        return sum(
            (line.credit for line in self.lines.all()),
            Decimal("0.00"),
        )

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit

    def __str__(self):
        return f"{self.entry_number} — {self.description}"


class JournalLine(models.Model):
    entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name="journal_lines",
    )
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(debit__gt=0, credit=0)
                    | Q(credit__gt=0, debit=0)
                ),
                name="fin_gl_line_one_side_positive",
            ),
        ]

    def clean(self):
        super().clean()

        if self.debit < 0 or self.credit < 0:
            raise ValidationError(
                "Journal line amounts cannot be negative."
            )

        if (self.debit > 0) == (self.credit > 0):
            raise ValidationError(
                "Enter a positive debit or credit, but not both."
            )

        if self.entry_id and self.entry.status != JournalEntry.DRAFT:
            raise ValidationError(
                "Lines can only be changed while an entry is in draft."
            )

    def __str__(self):
        side = (
            f"Dr {self.debit}"
            if self.debit > 0
            else f"Cr {self.credit}"
        )
        return f"{self.entry.entry_number} / {self.account.code} / {side}"


class CustomerAdvance(models.Model):
    PENDING = "PENDING"
    AVAILABLE = "AVAILABLE"
    PARTIALLY_APPLIED = "PARTIALLY_APPLIED"
    APPLIED = "APPLIED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"

    STATUSES = (
        (PENDING, "Pending"),
        (AVAILABLE, "Available"),
        (PARTIALLY_APPLIED, "Partially Applied"),
        (APPLIED, "Applied"),
        (PARTIALLY_REFUNDED, "Partially Refunded"),
        (REFUNDED, "Refunded"),
        (CANCELLED, "Cancelled"),
    )

    reference = models.CharField(max_length=60, unique=True, blank=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_customer_advances",
    )
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=50, blank=True)
    source_type = models.CharField(max_length=50)
    source_id = models.CharField(max_length=100)
    source_reference = models.CharField(max_length=120, blank=True)
    currency = models.CharField(max_length=3, default="RWF")
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    applied_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    refunded_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=30,
        choices=STATUSES,
        default=PENDING,
        db_index=True,
    )
    receipt_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="received_customer_advance",
    )
    received_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customer_advances",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id"],
                name="fin_unique_advance_source",
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="fin_advance_amount_positive",
            ),
            models.CheckConstraint(
                condition=Q(applied_amount__gte=0),
                name="fin_advance_applied_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(refunded_amount__gte=0),
                name="fin_advance_refunded_nonnegative",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                f"ADV-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:10].upper()}"
            )
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.applied_amount + self.refunded_amount > self.amount:
            raise ValidationError(
                "Applied and refunded amounts cannot exceed the advance."
            )

    @property
    def available_amount(self):
        return max(
            self.amount - self.applied_amount - self.refunded_amount,
            Decimal("0.00"),
        )

    def __str__(self):
        return f"{self.reference} — {self.customer_name}"
