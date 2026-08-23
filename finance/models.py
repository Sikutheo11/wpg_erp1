from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum
import uuid
from decimal import Decimal
from Employee.models import Employee
from inventory.models import (
    Asset,
    Product,
    RawMaterial,
    Supplier,
)
from sales.models import Sale
from accounts.models import User
from .general_ledger_models import (
    CustomerAdvance,
    JournalEntry,
    JournalLine,
    LedgerAccount,
)

from .identity import (
    normalize_bank_account,
    normalize_rwanda_phone,
)




# =====================================================
# ACCOUNT
# =====================================================

class Account(models.Model):

    ACCOUNT_TYPES = (
        ('cash','Cash'),
        ('bank','Bank'),
        ('mobile','Mobile Money'),
    )


    name = models.CharField(max_length=100)

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES
    )

    account_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )


    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.name


# =====================================================
# COUNTERPARTY
# =====================================================

class Counterparty(models.Model):
    """
    One person, company or institution that may owe WPG money,
    be owed money by WPG, or perform both roles.

    Phone and bank account identity fields prevent the same
    counterparty from being registered more than once.
    """

    INDIVIDUAL = "INDIVIDUAL"
    COMPANY = "COMPANY"
    INSTITUTION = "INSTITUTION"

    PARTY_TYPES = (
        (INDIVIDUAL, "Individual"),
        (COMPANY, "Company"),
        (INSTITUTION, "Institution"),
    )

    party_type = models.CharField(
        max_length=20,
        choices=PARTY_TYPES,
        default=INDIVIDUAL,
    )
    name = models.CharField(
        max_length=200,
    )
    phone = models.CharField(
        max_length=16,
        help_text=(
            "Rwanda telephone number, for example "
            "0788123456 or +250788123456."
        ),
    )
    phone_identity = models.CharField(
        max_length=9,
        unique=True,
        editable=False,
        help_text=(
            "Normalized Rwanda national number used "
            "for duplicate detection."
        ),
    )

    email = models.EmailField(
        blank=True,
    )
    address = models.TextField(
        blank=True,
    )
    tax_number = models.CharField(
        max_length=100,
        blank=True,
    )

    bank_name = models.CharField(
        max_length=120,
        blank=True,
    )
    bank_account_name = models.CharField(
        max_length=200,
        blank=True,
    )
    bank_account_number = models.CharField(
        max_length=100,
        blank=True,
    )
    bank_account_identity = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        help_text=(
            "Normalized bank account used for "
            "duplicate detection."
        ),
    )

    is_customer = models.BooleanField(
        default=False,
    )
    is_supplier = models.BooleanField(
        default=False,
    )
    is_active = models.BooleanField(
        default=True,
    )

    sales_customer = models.OneToOneField(
        "sales.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_counterparty",
    )
    inventory_supplier = models.OneToOneField(
        "inventory.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_counterparty",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    class Meta:
        ordering = [
            "name",
            "phone",
        ]
        verbose_name_plural = "counterparties"

    def clean(self):
        super().clean()

        normalized_phone, phone_identity = (
            normalize_rwanda_phone(self.phone)
        )
        self.phone = normalized_phone
        self.phone_identity = phone_identity

        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError(
                {"name": "Provide the person or company name."}
            )

        self.bank_name = (
            self.bank_name or ""
        ).strip()
        self.bank_account_name = (
            self.bank_account_name or ""
        ).strip()
        self.bank_account_number = (
            self.bank_account_number or ""
        ).strip()
        self.bank_account_identity = (
            normalize_bank_account(
                self.bank_account_number
            )
        )

        if (
            self.bank_account_number
            and not self.bank_name
        ):
            raise ValidationError(
                {
                    "bank_name": (
                        "Select or enter the bank when "
                        "an account number is provided."
                    )
                }
            )

    def save(self, *args, **kwargs):
        normalized_phone, phone_identity = (
            normalize_rwanda_phone(self.phone)
        )
        self.phone = normalized_phone
        self.phone_identity = phone_identity

        self.name = (self.name or "").strip()
        self.bank_name = (
            self.bank_name or ""
        ).strip()
        self.bank_account_name = (
            self.bank_account_name or ""
        ).strip()
        self.bank_account_number = (
            self.bank_account_number or ""
        ).strip()
        self.bank_account_identity = (
            normalize_bank_account(
                self.bank_account_number
            )
        )

        super().save(*args, **kwargs)

    @property
    def role_label(self):
        if self.is_customer and self.is_supplier:
            return "Customer and supplier"

        if self.is_customer:
            return "Customer"

        if self.is_supplier:
            return "Supplier"

        return "Unassigned"

    def __str__(self):
        return f"{self.name} — {self.phone}"


# =====================================================
# COUNTERPARTY DEBT RECORD
# =====================================================

class DebtRecord(models.Model):
    THEY_OWE_US = "THEY_OWE_US"
    WE_OWE_THEM = "WE_OWE_THEM"

    DIRECTIONS = (
        (
            THEY_OWE_US,
            "They owe WPG money",
        ),
        (
            WE_OWE_THEM,
            "WPG owes them money",
        ),
    )

    DRAFT = "DRAFT"
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

    STATUSES = (
        (DRAFT, "Draft"),
        (OPEN, "Open"),
        (PARTIAL, "Partially Paid"),
        (PAID, "Paid"),
        (OVERDUE, "Overdue"),
        (CANCELLED, "Cancelled"),
    )

    BUSINESS_UNITS = (
        ("GENERAL", "WPG General"),
        (
            "FURNITURE",
            "Furniture & Manufacturing",
        ),
        (
            "CONSTRUCTION",
            "Construction",
        ),
        (
            "AGRICULTURE",
            "Agriculture / Poultry",
        ),
        ("MARKETPLACE", "Marketplace"),
    )

    reference = models.CharField(
        max_length=60,
        unique=True,
        blank=True,
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        related_name="debt_records",
    )
    direction = models.CharField(
        max_length=20,
        choices=DIRECTIONS,
        db_index=True,
    )
    business_unit = models.CharField(
        max_length=30,
        choices=BUSINESS_UNITS,
        default="GENERAL",
        db_index=True,
    )
    transaction_date = models.DateField(
        default=timezone.localdate,
    )
    due_date = models.DateField(
        null=True,
        blank=True,
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    amount_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default=DRAFT,
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
    )

    receivable = models.OneToOneField(
        "finance.Receivable",
        on_delete=models.PROTECT,
        related_name="counterparty_debt_record",
        null=True,
        blank=True,
    )
    payable = models.OneToOneField(
        "finance.Payable",
        on_delete=models.PROTECT,
        related_name="counterparty_debt_record",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_counterparty_debts",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    class Meta:
        ordering = [
            "-transaction_date",
            "-pk",
        ]
        indexes = [
            models.Index(
                fields=[
                    "counterparty",
                    "direction",
                    "status",
                ],
                name="fin_debt_party_dir_status_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.total_amount < 0:
            raise ValidationError(
                {
                    "total_amount": (
                        "Total amount cannot be negative."
                    )
                }
            )

        if self.amount_paid < 0:
            raise ValidationError(
                {
                    "amount_paid": (
                        "Amount paid cannot be negative."
                    )
                }
            )

        if self.amount_paid > self.total_amount:
            raise ValidationError(
                {
                    "amount_paid": (
                        "Amount paid cannot exceed "
                        "the debt total."
                    )
                }
            )

        if (
            self.due_date
            and self.transaction_date
            and self.due_date < self.transaction_date
        ):
            raise ValidationError(
                {
                    "due_date": (
                        "Due date cannot be before "
                        "the transaction date."
                    )
                }
            )

        if self.direction == self.THEY_OWE_US:
            if self.payable_id:
                raise ValidationError(
                    {
                        "payable": (
                            "A receivable debt cannot be "
                            "linked to a payable."
                        )
                    }
                )

        if self.direction == self.WE_OWE_THEM:
            if self.receivable_id:
                raise ValidationError(
                    {
                        "receivable": (
                            "A payable debt cannot be "
                            "linked to a receivable."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = (
                f"DEBT-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )

        super().save(*args, **kwargs)

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def recalculate_total(self):
        total = (
            self.lines.aggregate(
                total=Sum("line_total")
            )["total"]
            or Decimal("0.00")
        )

        self.total_amount = total
        self.save(
            update_fields=[
                "total_amount",
                "updated_at",
            ]
        )

        return total

    def __str__(self):
        return (
            f"{self.reference} — "
            f"{self.counterparty.name}"
        )


class DebtLine(models.Model):

    PRODUCT = "PRODUCT"
    RAW_MATERIAL = "RAW_MATERIAL"
    ASSET = "ASSET"
    SERVICE = "SERVICE"
    OTHER = "OTHER"

    ITEM_TYPES = (
        (PRODUCT, "Product"),
        (RAW_MATERIAL, "Raw material"),
        (ASSET, "Asset"),
        (SERVICE, "Service"),
        (OTHER, "Other"),
    )

    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPES,
        default=OTHER,
        db_index=True,
    )
    debt = models.ForeignKey(
        DebtRecord,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="counterparty_debt_lines",
        null=True,
        blank=True,
    )
    raw_material = models.ForeignKey(
        RawMaterial,
        on_delete=models.PROTECT,
        related_name="counterparty_debt_lines",
        null=True,
        blank=True,
        help_text=(
            "Legacy raw material. New raw materials "
            "should normally use an Inventory Product."
        ),
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="counterparty_debt_lines",
        null=True,
        blank=True,
    )

    description = models.CharField(
        max_length=300,
        blank=True,
        help_text=(
            "Product or service supplied in this transaction."
        ),
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("1.000"),
    )
    unit = models.CharField(
        max_length=30,
        default="piece",
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )
    line_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    quantity__gt=0,
                ),
                name="fin_debt_line_qty_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    unit_price__gte=0,
                ),
                name="fin_debt_line_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        item_type="PRODUCT",
                        product__isnull=False,
                        raw_material__isnull=True,
                        asset__isnull=True,
                    )
                    | models.Q(
                        item_type="RAW_MATERIAL",
                        product__isnull=True,
                        raw_material__isnull=False,
                        asset__isnull=True,
                    )
                    | models.Q(
                        item_type="ASSET",
                        product__isnull=True,
                        raw_material__isnull=True,
                        asset__isnull=False,
                    )
                    | models.Q(
                        item_type__in=[
                            "SERVICE",
                            "OTHER",
                        ],
                        product__isnull=True,
                        raw_material__isnull=True,
                        asset__isnull=True,
                    )
                ),
                name="fin_debt_line_item_source_valid",
            ),
        ]

    def clean(self):
        super().clean()

        if self.quantity <= 0:
            raise ValidationError(
                {
                    "quantity": (
                        "Quantity must be greater than zero."
                    )
                }
            )

        if self.unit_price < 0:
            raise ValidationError(
                {
                    "unit_price": (
                        "Unit price cannot be negative."
                    )
                }
            )

        description = (
            self.description or ""
        ).strip()

        if self.item_type == self.PRODUCT:
            if not self.product_id:
                raise ValidationError(
                    {
                        "product": (
                            "Select the product supplied."
                        )
                    }
                )

            if self.raw_material_id or self.asset_id:
                raise ValidationError(
                    (
                        "A product line cannot also contain "
                        "a raw material or asset."
                    )
                )

        elif self.item_type == self.RAW_MATERIAL:
            if not self.raw_material_id:
                raise ValidationError(
                    {
                        "raw_material": (
                            "Select the raw material supplied."
                        )
                    }
                )

            if self.product_id or self.asset_id:
                raise ValidationError(
                    (
                        "A raw-material line cannot also "
                        "contain a product or asset."
                    )
                )

        elif self.item_type == self.ASSET:
            if not self.asset_id:
                raise ValidationError(
                    {
                        "asset": (
                            "Select the asset involved."
                        )
                    }
                )

            if self.product_id or self.raw_material_id:
                raise ValidationError(
                    (
                        "An asset line cannot also contain "
                        "a product or raw material."
                    )
                )

        elif self.item_type in {
            self.SERVICE,
            self.OTHER,
        }:
            if not description:
                raise ValidationError(
                    {
                        "description": (
                            "Describe the service or item."
                        )
                    }
                )

            if (
                self.product_id
                or self.raw_material_id
                or self.asset_id
            ):
                raise ValidationError(
                    (
                        "A service or other line cannot "
                        "reference an inventory item."
                    )
                )

        else:
            raise ValidationError(
                {
                    "item_type": (
                        "Select a valid item type."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if (
            self.item_type == self.PRODUCT
            and self.product_id
            and not (self.description or "").strip()
        ):
            self.description = self.product.name

        elif (
            self.item_type == self.RAW_MATERIAL
            and self.raw_material_id
            and not (self.description or "").strip()
        ):
            self.description = self.raw_material.name

        elif (
            self.item_type == self.ASSET
            and self.asset_id
            and not (self.description or "").strip()
        ):
            self.description = self.asset.name

        self.description = (
            self.description or ""
        ).strip()
        self.unit = (
            self.unit or "piece"
        ).strip()

        self.line_total = (
            Decimal(str(self.quantity))
            * Decimal(str(self.unit_price))
        ).quantize(
            Decimal("0.01")
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.description} — "
            f"{self.line_total}"
        )


# =====================================================
# TRANSACTION
# =====================================================

class Transaction(models.Model):

    TYPES = (
        ('income','Income'),
        ('expense','Expense'),
    )


    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions"
    )


    transaction_type=models.CharField(
        max_length=20,
        choices=TYPES
    )


    amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    description=models.CharField(
        max_length=255
    )


    date=models.DateField(
        default=timezone.now
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.description





# =====================================================
# INCOME
# =====================================================

class Income(models.Model):


    INCOME_TYPES = (

        ('sales','Sales'),
        ('construction','Construction'),
        ('furniture','Furniture'),
        ('service','Service'),
        ('other','Other'),

    )


    account=models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )


    title=models.CharField(
        max_length=200,
        blank=True,
        null=True
    )


    income_type=models.CharField(
        max_length=50,
        choices=INCOME_TYPES,
        default="other"
    )


    amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    sale=models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    date=models.DateField(
        default=timezone.now
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )



    def save(self,*args,**kwargs):

        is_new=self.pk is None

        super().save(*args,**kwargs)


        if is_new and self.account:

            self.account.balance += self.amount
            self.account.save()


            Transaction.objects.create(
                account=self.account,
                transaction_type="income",
                amount=self.amount,
                description=self.title or "Income"
            )


    def __str__(self):
        return self.title or "Income"





# =====================================================
# EXPENSE
# =====================================================

class Expense(models.Model):


    EXPENSE_TYPES=(

        ('salary','Salary'),
        ('rent','Rent'),
        ('transport','Transport'),
        ('raw_material','Raw Material'),
        ('maintenance','Maintenance'),
        ('other','Other'),

    )


    account=models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )


    title=models.CharField(
        max_length=200,
        blank=True,
        null=True
    )


    expense_type=models.CharField(
        max_length=50,
        choices=EXPENSE_TYPES
    )


    amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    supplier=models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    date=models.DateField(
        default=timezone.now
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )



    def save(self,*args,**kwargs):

        is_new=self.pk is None

        super().save(*args,**kwargs)


        if is_new and self.account:

            self.account.balance -= self.amount
            self.account.save()


            Transaction.objects.create(
                account=self.account,
                transaction_type="expense",
                amount=self.amount,
                description=self.title or "Expense"
            )



    def __str__(self):
        return self.title or "Expense"





# =====================================================
# RECEIVABLE (CUSTOMER DEBT)
# =====================================================

class ObligationItemGroup(models.Model):
    BUSINESS_UNITS = (
        ("FURNITURE", "Furniture & Manufacturing"),
        ("CONSTRUCTION", "Construction & Built Environment"),
        ("AGRICULTURE", "Agriculture & Poultry"),
    )

    business_unit = models.CharField(max_length=30, choices=BUSINESS_UNITS, db_index=True)
    name = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("business_unit", "order", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("business_unit", "name"),
                name="fin_item_group_unique_name",
            )
        ]

    def __str__(self):
        return self.name


class ObligationItemType(models.Model):
    item_group = models.ForeignKey(
        ObligationItemGroup,
        on_delete=models.PROTECT,
        related_name="item_types",
    )
    name = models.CharField(max_length=120)
    default_unit = models.CharField(max_length=30, default="piece")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("item_group__order", "order", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("item_group", "name"),
                name="fin_item_type_unique_name",
            )
        ]

    def __str__(self):
        return self.name

class Receivable(models.Model):

    STATUS = (
        ("unpaid", "Unpaid"),
        ("partial", "Partial"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
    )

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="receivable",
        null=True,
        blank=True,
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        related_name="receivables",
        null=True,
        blank=True,
    )
    business_unit = models.CharField(
        max_length=30,
        choices=DebtRecord.BUSINESS_UNITS,
        default="GENERAL",
        db_index=True,
    )
    item_group = models.ForeignKey(
        ObligationItemGroup,
        on_delete=models.PROTECT,
        related_name="receivables",
        null=True,
        blank=True,
    )
    transaction_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    invoice_number = models.CharField(
        max_length=100,
        unique=True,
    )

    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    amount_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    due_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="unpaid",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def __str__(self):
        return self.invoice_number





# =====================================================
# PAYABLE (SUPPLIER DEBT)
# =====================================================

class Payable(models.Model):


    supplier=models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        related_name="payables",
        null=True,
        blank=True,
    )
    business_unit = models.CharField(
        max_length=30,
        choices=DebtRecord.BUSINESS_UNITS,
        default="GENERAL",
        db_index=True,
    )
    item_group = models.ForeignKey(
        ObligationItemGroup,
        on_delete=models.PROTECT,
        related_name="payables",
        null=True,
        blank=True,
    )
    transaction_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)


    reference=models.CharField(
        max_length=100,
        unique=True,
    )


    total_amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    amount_paid=models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    due_date=models.DateField()


    STATUS=(

        ('unpaid','Unpaid'),
        ('partial','Partial'),
        ('paid','Paid'),
        ('overdue','Overdue'),

    )


    status=models.CharField(
        max_length=20,
        choices=STATUS,
        default="unpaid"
    )



    created_at=models.DateTimeField(
        auto_now_add=True
    )



    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def save(self, *args, **kwargs):
        if self.amount_paid >= self.total_amount:
            self.status = "paid"
        elif self.amount_paid > 0:
            self.status = "partial"
        elif self.due_date and self.due_date < timezone.localdate():
            self.status = "overdue"
        else:
            self.status = "unpaid"
        super().save(*args, **kwargs)


class ObligationLine(models.Model):
    PRODUCT = "PRODUCT"
    RAW_MATERIAL = "RAW_MATERIAL"
    ASSET = "ASSET"
    WORKER = "WORKER"
    TAX = "TAX"
    CASUAL_WORK = "CASUAL_WORK"
    TRANSPORT = "TRANSPORT"
    RENT = "RENT"
    UTILITY = "UTILITY"
    SERVICE = "SERVICE"
    OTHER = "OTHER"

    ITEM_TYPES = (
        (PRODUCT, "Product"),
        (RAW_MATERIAL, "Raw material"),
        (ASSET, "Asset"),
        (WORKER, "Worker"),
        (TAX, "Tax"),
        (CASUAL_WORK, "Casual work"),
        (TRANSPORT, "Transport"),
        (RENT, "Rent"),
        (UTILITY, "Utility"),
        (SERVICE, "Service"),
        (OTHER, "Other"),
    )

    receivable = models.ForeignKey(
        Receivable, on_delete=models.CASCADE, related_name="lines", null=True, blank=True
    )
    payable = models.ForeignKey(
        Payable, on_delete=models.CASCADE, related_name="lines", null=True, blank=True
    )
    catalog_item = models.ForeignKey(
        ObligationItemType,
        on_delete=models.PROTECT,
        related_name="obligation_lines",
        null=True,
        blank=True,
    )
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default=OTHER)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, null=True, blank=True)
    worker = models.ForeignKey(Employee, on_delete=models.PROTECT, null=True, blank=True)
    description = models.CharField(max_length=300, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("1.000"))
    unit = models.CharField(max_length=30, default="piece")
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(receivable__isnull=False, payable__isnull=True)
                    | models.Q(receivable__isnull=True, payable__isnull=False)
                ),
                name="fin_obligation_line_one_parent",
            ),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="fin_obligation_line_qty_gt_zero"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="fin_obligation_line_price_nonnegative"),
        ]

    def clean(self):
        super().clean()
        has_receivable = bool(self.receivable_id or getattr(self, "receivable", None))
        has_payable = bool(self.payable_id or getattr(self, "payable", None))
        if has_receivable == has_payable:
            raise ValidationError("A line must belong to one receivable or one payable.")
        if self.catalog_item_id:
            parent = self.receivable or self.payable
            if parent and parent.item_group_id != self.catalog_item.item_group_id:
                raise ValidationError({"catalog_item": "Select an item from the chosen item group."})
            if any((self.product_id, self.raw_material_id, self.asset_id, self.worker_id)):
                raise ValidationError("A catalog item cannot also use a legacy item source.")
            if self.quantity <= 0 or self.unit_price < 0:
                raise ValidationError("Quantity and unit price are invalid.")
            return
        sources = [self.product_id, self.raw_material_id, self.asset_id, self.worker_id]
        expected = {
            self.PRODUCT: self.product_id,
            self.RAW_MATERIAL: self.raw_material_id,
            self.ASSET: self.asset_id,
            self.WORKER: self.worker_id,
        }
        if self.item_type in expected:
            if not expected[self.item_type] or sum(bool(value) for value in sources) != 1:
                raise ValidationError("Select the matching item for this line type.")
        elif any(sources):
            raise ValidationError("This line type must use a description, not an inventory item.")
        if self.item_type not in expected and not (self.description or "").strip():
            # New payable/receivable forms intentionally hide the legacy
            # description field and use catalog_item instead.  A field-bound
            # error for an excluded field makes ModelForm raise ValueError;
            # keep this as a non-field validation error instead.
            raise ValidationError("Select an item type for this obligation line.")
        if self.quantity <= 0 or self.unit_price < 0:
            raise ValidationError("Quantity and unit price are invalid.")

    def save(self, *args, **kwargs):
        if self.catalog_item_id:
            self.item_type = self.OTHER
            self.description = self.catalog_item.name
            self.unit = self.catalog_item.default_unit
        source = self.product or self.raw_material or self.asset or self.worker
        if source and not (self.description or "").strip():
            self.description = str(source)
        self.description = (self.description or "").strip()
        self.unit = (self.unit or "piece").strip()
        self.line_total = (Decimal(str(self.quantity)) * Decimal(str(self.unit_price))).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)





# =====================================================
# PAYMENT
# =====================================================

class Payment(models.Model):


    METHODS=(

        ('cash','Cash'),
        ('bank','Bank'),
        ('mobile_money','Mobile Money'),

    )


    amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    method=models.CharField(
        max_length=30,
        choices=METHODS
    )


    receivable=models.ForeignKey(
        Receivable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    payable=models.ForeignKey(
        Payable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    date=models.DateField(
        auto_now_add=True
    )


    notes=models.TextField(
        blank=True
    )


    def clean(self):

        if not self.receivable and not self.payable:

            raise ValidationError(
                "Payment must belong to receivable or payable"
            )


        if self.receivable and self.payable:

            raise ValidationError(
                "Payment cannot be both"
            )



    def save(self,*args,**kwargs):

        self.clean()

        super().save(*args,**kwargs)


        if self.receivable:

            self.receivable.amount_paid += self.amount
            self.receivable.save()



        if self.payable:

            self.payable.amount_paid += self.amount
            self.payable.save()




# =====================================================
# PAYROLL
# =====================================================

class Payroll(models.Model):


    employee=models.ForeignKey(
        Employee,
        on_delete=models.CASCADE
    )


    month=models.DateField()



    basic_salary=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    overtime_hours=models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )


    overtime_rate=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )


    deductions=models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    gross_salary=models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    net_salary=models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )



    def save(self,*args,**kwargs):

        overtime=self.overtime_hours*self.overtime_rate

        self.gross_salary=self.basic_salary+overtime

        self.net_salary=self.gross_salary-self.deductions


        super().save(*args,**kwargs)



    def __str__(self):

        return f"{self.employee}-{self.month}"





# =====================================================
# FINANCIAL REPORT
# =====================================================

def calculate_financial_summary(start_date,end_date):


    income=Income.objects.filter(
        date__range=(start_date,end_date)
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0



    expense=Expense.objects.filter(
        date__range=(start_date,end_date)
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0



    receivable=Receivable.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0



    payable=Payable.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0



    return {

        "income":income,

        "expense":expense,

        "receivable":receivable,

        "payable":payable,

        "profit":
        (income+receivable)-(expense+payable)

    }

from .general_ledger_models import (
    CustomerAdvance,
    JournalEntry,
    JournalLine,
    LedgerAccount,
)
