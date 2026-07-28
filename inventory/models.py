from decimal import Decimal
import random
import string
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.text import slugify

from Employee.models import Department, Employee


BUSINESS_UNIT_CHOICES = (
    ("FURNITURE", "Furniture & Manufacturing"),
    ("CONSTRUCTION", "Construction"),
    ("AGRICULTURE", "Agriculture / Poultry"),
    ("MARKETPLACE", "Marketplace"),
)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    WAREHOUSE_TYPES = (
        ("MAIN", "Main Warehouse"),
        ("RAW_MATERIAL", "Raw Material Store"),
        ("FINISHED_GOODS", "Finished Goods Store"),
        ("PROJECT", "Construction Project Store"),
        ("FARM", "Agriculture / Farm Store"),
        ("SHOP", "Shop / Marketplace Store"),
        ("TRANSIT", "Transit Warehouse"),
        ("OTHER", "Other"),
    )

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, blank=True, default="",)
    warehouse_type = models.CharField(
        max_length=30,
        choices=WAREHOUSE_TYPES,
        default="MAIN",
    )
    business_unit = models.CharField(
        max_length=30,
        choices=BUSINESS_UNIT_CHOICES,
        blank=True,
    )
    location = models.CharField(max_length=200, blank=True)
    manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_warehouses",
    )
    is_active = models.BooleanField(default=True)
    allow_negative_stock = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["warehouse_type", "name"]

    def save(self, *args, **kwargs):
        if not self.code:
            base_code = (
                slugify(self.name).replace("-", "_").upper()[:25]
                or "WAREHOUSE"
            )
            code = base_code
            suffix = 1

            while Warehouse.objects.exclude(pk=self.pk).filter(code=code).exists():
                suffix += 1
                code = f"{base_code[:20]}_{suffix}"

            self.code = code

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    tax_number = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RawMaterial(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("disposed", "Disposed"),
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )
    unit = models.CharField(max_length=20, default="Kg")
    minimum_stock = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    linked_product = models.OneToOneField(
        "Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legacy_raw_material",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    @property
    def current_stock(self):
        inbound_types = {
            "IN",
            "TRANSFER_IN",
            "ADJUSTMENT_IN",
            "RETURN_IN",
        }
        outbound_types = {
            "OUT",
            "TRANSFER_OUT",
            "ADJUSTMENT_OUT",
            "RETURN_OUT",
        }

        stock_in = (
            StockMovement.objects.filter(
                raw_material=self,
                movement_type__in=inbound_types,
                status="POSTED",
            ).aggregate(total=Sum("quantity"))["total"]
            or Decimal("0.00")
        )

        stock_out = (
            StockMovement.objects.filter(
                raw_material=self,
                movement_type__in=outbound_types,
                status="POSTED",
            ).aggregate(total=Sum("quantity"))["total"]
            or Decimal("0.00")
        )

        return stock_in - stock_out

    @property
    def needs_restock(self):
        return self.current_stock <= self.minimum_stock

    def __str__(self):
        return self.name


class Product(models.Model):
    BUSINESS_UNITS = BUSINESS_UNIT_CHOICES

    PRODUCT_TYPES = (
        ("RAW_MATERIAL", "Raw Material"),
        ("FINISHED_GOOD", "Finished Good"),
        ("CONSUMABLE", "Consumable"),
        ("AGRICULTURE_INPUT", "Agriculture Input"),
        ("AGRICULTURE_OUTPUT", "Agriculture Output"),
        ("LIVESTOCK", "Livestock"),
        ("SERVICE", "Service"),
        ("CUSTOM", "Custom Product"),
    )

    VALUATION_METHODS = (
        ("STANDARD", "Standard Cost"),
        ("WEIGHTED_AVERAGE", "Weighted Average"),
        ("FIFO", "FIFO"),
    )

    business_unit = models.CharField(
        max_length=30,
        choices=BUSINESS_UNITS,
        default="FURNITURE",
    )
    product_type = models.CharField(
        max_length=30,
        choices=PRODUCT_TYPES,
        default="FINISHED_GOOD",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    preferred_supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_products",
    )
    product_code = models.CharField(max_length=50, unique=True, blank=True)
    barcode = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, default="pcs")
    selling_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    standard_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    reorder_level = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    reorder_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    valuation_method = models.CharField(
        max_length=30,
        choices=VALUATION_METHODS,
        default="STANDARD",
    )
    track_inventory = models.BooleanField(default=True)
    allow_negative_stock = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["business_unit", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(selling_price__gte=0),
                name="inventory_product_selling_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(standard_cost__gte=0),
                name="inventory_product_standard_cost_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(reorder_level__gte=0),
                name="inventory_product_reorder_level_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(reorder_quantity__gte=0),
                name="inventory_product_reorder_quantity_non_negative",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.product_code:
            prefix = self.name[:3].upper().replace(" ", "") or "PRD"
            last_id = (
                Product.objects.order_by("-id")
                .values_list("id", flat=True)
                .first()
                or 0
            )
            self.product_code = f"{prefix}-{last_id + 1:05d}"

        if not self.slug:
            base_slug = slugify(self.name) or "product"
            product_slug = base_slug
            suffix = 1

            while Product.objects.exclude(pk=self.pk).filter(
                slug=product_slug
            ).exists():
                suffix += 1
                product_slug = f"{base_slug}-{suffix}"

            self.slug = product_slug

        if self.product_type == "SERVICE":
            self.track_inventory = False

        super().save(*args, **kwargs)

    @property
    def current_stock(self):
        if not self.track_inventory:
            return Decimal("0.00")

        from inventory.services import StockService

        return StockService.actual_stock(product=self)

    @property
    def needs_restock(self):
        if not self.track_inventory:
            return False

        return self.current_stock <= self.reorder_level

    def __str__(self):
        return f"{self.name} ({self.product_code})"


class Asset(models.Model):
    ASSET_TYPES = (
        ("machine", "Machine"),
        ("vehicle", "Vehicle"),
        ("computer", "Computer"),
        ("tool", "Tool"),
        ("furniture", "Furniture"),
        ("other", "Other"),
    )

    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("maintenance", "Maintenance"),
        ("disposed", "Disposed"),
    )

    asset_type = models.CharField(max_length=50, choices=ASSET_TYPES)
    name = models.CharField(max_length=200)
    asset_code = models.CharField(max_length=100, unique=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=15, decimal_places=2)
    purchase_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_code(self):
        prefix = self.asset_type[:3].upper()
        random_part = "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=6,
            )
        )
        return f"{prefix}-{random_part}"

    def save(self, *args, **kwargs):
        if not self.asset_code:
            code = self.generate_code()

            while Asset.objects.filter(asset_code=code).exists():
                code = self.generate_code()

            self.asset_code = code

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.asset_code})"


class AssetAssignment(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_date = models.DateField()
    returned_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return str(self.asset)


class StockMovement(models.Model):
    MOVEMENT_TYPES = (
        ("IN", "Stock In"),
        ("OUT", "Stock Out"),
        ("TRANSFER_IN", "Transfer In"),
        ("TRANSFER_OUT", "Transfer Out"),
        ("ADJUSTMENT_IN", "Positive Adjustment"),
        ("ADJUSTMENT_OUT", "Negative Adjustment"),
        ("RETURN_IN", "Return In"),
        ("RETURN_OUT", "Return Out"),
    )

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("POSTED", "Posted"),
        ("REVERSED", "Reversed"),
        ("CANCELLED", "Cancelled"),
    )

    REFERENCE_TYPES = (
        ("OPENING_BALANCE", "Opening Balance"),
        ("PURCHASE", "Purchase"),
        ("SALES_ORDER", "Sales Order"),
        ("ECOMMERCE_ORDER", "Ecommerce Order"),
        ("PRODUCTION_JOB", "Furniture Production Job"),
        ("CONSTRUCTION_PROJECT", "Construction Project"),
        ("AGRICULTURE_OPERATION", "Agriculture Operation"),
        ("FEED_CONSUMPTION", "Feed Consumption"),
        ("EGG_COLLECTION", "Egg Collection"),
        ("INCUBATION", "Incubation"),
        ("TRANSFER", "Warehouse Transfer"),
        ("RETURN", "Stock Return"),
        ("STOCK_COUNT", "Stock Count"),
        ("ADJUSTMENT", "Manual Adjustment"),
        ("OTHER", "Other"),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    raw_material = models.ForeignKey(
        RawMaterial,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
        help_text="Legacy field. New movements should use product.",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    movement_type = models.CharField(
        max_length=30,
        choices=MOVEMENT_TYPES,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="POSTED",
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    business_unit = models.CharField(
        max_length=30,
        choices=BUSINESS_UNIT_CHOICES,
        blank=True,
    )
    reference_type = models.CharField(
        max_length=40,
        choices=REFERENCE_TYPES,
        default="OTHER",
    )
    reference_id = models.CharField(max_length=100, blank=True)
    reference_no = models.CharField(max_length=100, blank=True)
    transfer_group = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )
    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversal_movement",
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_stock_movements_created",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["product", "warehouse", "movement_type"],
                name="inv_move_prod_wh_type_idx",
            ),
            models.Index(
                fields=["reference_type", "reference_id"],
                name="inv_move_reference_idx",
            ),
            models.Index(
                fields=["business_unit", "created_at"],
                name="inv_move_unit_date_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="inv_move_status_date_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="inventory_movement_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0),
                name="inventory_movement_unit_cost_non_negative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(product__isnull=False)
                    | models.Q(raw_material__isnull=False)
                ),
                name="inventory_movement_requires_stock_item",
            ),
        ]

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost

    @property
    def is_inbound(self):
        return self.movement_type in {
            "IN",
            "TRANSFER_IN",
            "ADJUSTMENT_IN",
            "RETURN_IN",
        }

    @property
    def is_outbound(self):
        return self.movement_type in {
            "OUT",
            "TRANSFER_OUT",
            "ADJUSTMENT_OUT",
            "RETURN_OUT",
        }

    def clean(self):
        super().clean()

        if self.product and self.raw_material:
            raise ValidationError(
                "A stock movement cannot reference both a Product and a RawMaterial."
            )

        if not self.product and not self.raw_material:
            raise ValidationError(
                "Select a Product or legacy RawMaterial."
            )

        if self.product and not self.product.track_inventory:
            raise ValidationError(
                {"product": "This product does not track inventory."}
            )

        if (
            self.movement_type in {"TRANSFER_IN", "TRANSFER_OUT"}
            and not self.transfer_group
        ):
            self.transfer_group = uuid.uuid4()

    def __str__(self):
        stock_item = self.product or self.raw_material
        return f"{stock_item} — {self.movement_type} {self.quantity}"


class StockReservation(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("RESERVED", "Reserved"),
        ("PARTIAL", "Partially Reserved"),
        ("FAILED", "Failed"),
        ("RELEASED", "Released"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )

    order_item = models.OneToOneField(
        "orders.OrderItem",
        on_delete=models.CASCADE,
        related_name="stock_reservation",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_reservations",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stock_reservations",
    )
    requested_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    reserved_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    completed_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_reservations_created",
    )
    reserved_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(requested_quantity__gt=0),
                name="inventory_reservation_requested_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_quantity__gte=0),
                name="inventory_reservation_reserved_quantity_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(completed_quantity__gte=0),
                name="inventory_reservation_completed_quantity_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    reserved_quantity__lte=models.F("requested_quantity")
                ),
                name="inventory_reservation_reserved_not_above_requested",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    completed_quantity__lte=models.F("reserved_quantity")
                ),
                name="inventory_reservation_completed_not_above_reserved",
            ),
        ]

    @property
    def shortage_quantity(self):
        shortage = self.requested_quantity - self.reserved_quantity
        return max(shortage, Decimal("0.00"))

    @property
    def remaining_reserved_quantity(self):
        remaining = self.reserved_quantity - self.completed_quantity
        return max(remaining, Decimal("0.00"))

    def __str__(self):
        return (
            f"{self.product.name} — "
            f"{self.reserved_quantity}/"
            f"{self.requested_quantity}"
        )
