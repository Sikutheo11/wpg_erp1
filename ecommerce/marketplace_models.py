import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


ZERO = Decimal("0.00")


class MarketplaceSeller(models.Model):
    """A WPG business unit or an independent Marketplace supplier."""

    WPG_INTERNAL = "WPG_INTERNAL"
    INDEPENDENT = "INDEPENDENT"

    SELLER_TYPES = (
        (WPG_INTERNAL, "WPG-owned business"),
        (INDEPENDENT, "Independent seller"),
    )

    code = models.CharField(max_length=40, unique=True, blank=True, editable=False)
    name = models.CharField(max_length=180)
    seller_type = models.CharField(
        max_length=20,
        choices=SELLER_TYPES,
        default=INDEPENDENT,
        db_index=True,
    )
    poultry_farm = models.OneToOneField(
        "agriculture.PoultryFarm",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketplace_seller",
        help_text="Optional farm represented by this seller account.",
    )
    contact_name = models.CharField(max_length=180, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    default_commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=ZERO,
        validators=[
            MinValueValidator(ZERO),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text="Percentage retained by WPG on independent-seller sales.",
    )
    payable_account = models.ForeignKey(
        "finance.LedgerAccount",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketplace_sellers",
        help_text="Seller Payable control/sub-ledger account.",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_marketplace_sellers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "code"]
        indexes = [
            models.Index(
                fields=["seller_type", "is_active"],
                name="ecom_seller_type_active_idx",
            ),
        ]

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()

        if self.seller_type == self.WPG_INTERNAL:
            self.default_commission_rate = ZERO

        if (
            self.seller_type == self.INDEPENDENT
            and self.default_commission_rate <= ZERO
        ):
            raise ValidationError(
                {
                    "default_commission_rate": (
                        "An independent seller needs a commission rate "
                        "greater than zero."
                    )
                }
            )
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = (
                f"SELLER-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )

        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @property
    def is_internal(self):
        return self.seller_type == self.WPG_INTERNAL

    def __str__(self):
        return f"{self.code} - {self.name}"


class SellerProductAssignment(models.Model):
    """Identifies who owns and fulfils one online product listing."""

    online_product = models.OneToOneField(
        "ecommerce.OnlineProduct",
        on_delete=models.PROTECT,
        related_name="seller_assignment",
    )
    seller = models.ForeignKey(
        MarketplaceSeller,
        on_delete=models.PROTECT,
        related_name="product_assignments",
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(ZERO),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text="Leave empty to use the seller's default commission rate.",
    )
    effective_from = models.DateField(default=timezone.localdate)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["online_product_id"]
        indexes = [
            models.Index(
                fields=["seller", "is_active"],
                name="ecom_assignment_seller_idx",
            ),
        ]

    @property
    def effective_commission_rate(self):
        if self.seller.is_internal:
            return ZERO
        if self.commission_rate is not None:
            return self.commission_rate
        return self.seller.default_commission_rate

    def clean(self):
        super().clean()
        if self.seller_id and self.seller.is_internal:
            self.commission_rate = ZERO

    def __str__(self):
        return f"{self.online_product} / {self.seller}"


class MarketplaceOrderLine(models.Model):
    """Immutable seller and commission snapshot for an OrderItem."""

    UNSETTLED = "UNSETTLED"
    ELIGIBLE = "ELIGIBLE"
    IN_SETTLEMENT = "IN_SETTLEMENT"
    SETTLED = "SETTLED"
    REVERSED = "REVERSED"

    STATUSES = (
        (UNSETTLED, "Unsettled"),
        (ELIGIBLE, "Eligible for settlement"),
        (IN_SETTLEMENT, "Included in settlement"),
        (SETTLED, "Settled"),
        (REVERSED, "Reversed"),
    )

    order_item = models.OneToOneField(
        "orders.OrderItem",
        on_delete=models.PROTECT,
        related_name="marketplace_line",
    )
    online_product = models.ForeignKey(
        "ecommerce.OnlineProduct",
        on_delete=models.PROTECT,
        related_name="marketplace_order_lines",
    )
    seller = models.ForeignKey(
        MarketplaceSeller,
        on_delete=models.PROTECT,
        related_name="order_lines",
    )
    farm = models.ForeignKey(
        "agriculture.PoultryFarm",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketplace_order_lines",
    )
    seller_code = models.CharField(max_length=40)
    seller_name = models.CharField(max_length=180)
    product_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    gross_amount = models.DecimalField(max_digits=15, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=15, decimal_places=2)
    seller_net_amount = models.DecimalField(max_digits=15, decimal_places=2)
    settlement_status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default=UNSETTLED,
        db_index=True,
    )
    eligible_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order_item__order_id", "order_item_id"]
        indexes = [
            models.Index(
                fields=["seller", "settlement_status"],
                name="ecom_line_seller_status_idx",
            ),
            models.Index(
                fields=["farm", "settlement_status"],
                name="ecom_line_farm_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="ecom_market_line_qty_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="ecom_market_line_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(gross_amount__gte=0),
                name="ecom_market_line_gross_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(commission_amount__gte=0),
                name="ecom_market_line_comm_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(seller_net_amount__gte=0),
                name="ecom_market_line_net_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()
        expected_gross = self.quantity * self.unit_price
        expected_commission = (
            expected_gross * self.commission_rate / Decimal("100.00")
        ).quantize(Decimal("0.01"))
        expected_net = expected_gross - expected_commission

        errors = {}
        if self.gross_amount != expected_gross:
            errors["gross_amount"] = "Gross amount does not match quantity × price."
        if self.commission_amount != expected_commission:
            errors["commission_amount"] = "Commission amount is incorrect."
        if self.seller_net_amount != expected_net:
            errors["seller_net_amount"] = "Seller net amount is incorrect."
        if errors:
            raise ValidationError(errors)

    @property
    def is_internal_sale(self):
        return self.seller.is_internal

    def __str__(self):
        return f"{self.order_item} / {self.seller_name}"


class SellerSettlement(models.Model):
    """One approved payment from WPG to an independent seller."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

    STATUSES = (
        (DRAFT, "Draft"),
        (APPROVED, "Approved"),
        (PAID, "Paid"),
        (CANCELLED, "Cancelled"),
    )

    settlement_number = models.CharField(max_length=60, unique=True, blank=True)
    seller = models.ForeignKey(
        MarketplaceSeller,
        on_delete=models.PROTECT,
        related_name="settlements",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default=DRAFT,
        db_index=True,
    )
    total_gross = models.DecimalField(max_digits=15, decimal_places=2, default=ZERO)
    total_commission = models.DecimalField(
        max_digits=15, decimal_places=2, default=ZERO
    )
    total_payable = models.DecimalField(max_digits=15, decimal_places=2, default=ZERO)
    payment_reference = models.CharField(max_length=120, blank=True)
    journal_entry = models.OneToOneField(
        "finance.JournalEntry",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="seller_settlement",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_seller_settlements",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_seller_settlements",
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paid_seller_settlements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["seller", "status"],
                name="ecom_settle_seller_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_gross__gte=0),
                name="ecom_settle_gross_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(total_commission__gte=0),
                name="ecom_settle_comm_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(total_payable__gte=0),
                name="ecom_settle_payable_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()
        if self.seller_id and self.seller.is_internal:
            raise ValidationError(
                {"seller": "WPG-owned sellers do not require settlements."}
            )
        if self.total_payable != self.total_gross - self.total_commission:
            raise ValidationError(
                {"total_payable": "Payable must equal gross minus commission."}
            )

    def save(self, *args, **kwargs):
        if not self.settlement_number:
            self.settlement_number = (
                f"SET-{timezone.localdate():%Y%m%d}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.settlement_number} - {self.seller.name}"


class SellerSettlementLine(models.Model):
    settlement = models.ForeignKey(
        SellerSettlement,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    marketplace_order_line = models.OneToOneField(
        MarketplaceOrderLine,
        on_delete=models.PROTECT,
        related_name="settlement_line",
    )
    gross_amount = models.DecimalField(max_digits=15, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=15, decimal_places=2)
    payable_amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["settlement_id", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(gross_amount__gte=0),
                name="ecom_settle_line_gross_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(commission_amount__gte=0),
                name="ecom_settle_line_comm_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(payable_amount__gte=0),
                name="ecom_settle_line_pay_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()
        line = self.marketplace_order_line
        errors = {}
        if self.settlement_id and line.seller_id != self.settlement.seller_id:
            errors["marketplace_order_line"] = "The order line belongs to another seller."
        if self.gross_amount != line.gross_amount:
            errors["gross_amount"] = "Gross amount must match the marketplace order line."
        if self.commission_amount != line.commission_amount:
            errors["commission_amount"] = "Commission must match the marketplace order line."
        if self.payable_amount != line.seller_net_amount:
            errors["payable_amount"] = "Payable must match the marketplace order line."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.settlement} / {self.marketplace_order_line}"
