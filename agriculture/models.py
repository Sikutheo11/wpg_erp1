from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PoultryFarm(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150, unique=True)
    location = models.CharField(max_length=255, blank=True)
    manager = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_poultry_farms",
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="poultry_farms",
        help_text="Agriculture inventory store serving this farm.",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()
        if self.warehouse_id:
            business_unit = getattr(self.warehouse, "business_unit", "")
            if business_unit and business_unit != "AGRICULTURE":
                raise ValidationError(
                    {"warehouse": "The warehouse must belong to Agriculture / Poultry."}
                )

    def __str__(self):
        return f"{self.code} - {self.name}"


class AgricultureOperation(TimeStampedModel):
    """
    Integration anchor between Poultry Operations and WPG BOS enterprise engines.

    Direct relationships are limited to shared master/transaction records:
    - accounts: created/approved users;
    - Employee: assigned operational owner;
    - Orders: optional enterprise order that initiated the operation.

    Sales, Ecommerce and Customer reach Agriculture through the source Order.
    Inventory and Finance are posted by services and correlated by this operation code.
    Core Workflow/Event Engine controls transitions, permissions, audit and notifications.
    """

    WORKFLOW_NAME = "AGRICULTURE_OPERATION"
    BUSINESS_UNIT = "AGRICULTURE"

    OPERATION_TYPES = (
        ("FLOCK_SETUP", "Flock Setup"),
        ("EGG_PRODUCTION", "Egg Production"),
        ("INCUBATION", "Incubation and Hatching"),
        ("BROODING", "Chick Brooding"),
        ("GROW_OUT", "Bird Grow-out"),
        ("FEEDING", "Feeding Programme"),
        ("HEALTH", "Health and Vaccination"),
        ("RESTOCK", "Inventory Restock"),
        ("ORDER_FULFILMENT", "Customer Order Fulfilment"),
        ("OTHER", "Other"),
    )

    STATUSES = (
        ("DRAFT", "Draft"),
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("ACTIVE", "Active"),
        ("ON_HOLD", "On Hold"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )

    code = models.CharField(max_length=50, unique=True)
    operation_type = models.CharField(
        max_length=30,
        choices=OPERATION_TYPES,
        db_index=True,
    )
    farm = models.ForeignKey(
        PoultryFarm,
        on_delete=models.PROTECT,
        related_name="operations",
    )
    source_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="agriculture_operations",
        help_text=(
            "Enterprise order created by Sales, Ecommerce, POS, restock "
            "or another approved order source."
        ),
    )
    assigned_to = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_agriculture_operations",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="DRAFT",
        db_index=True,
    )
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    actual_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Operational cost synchronized from Finance postings.",
    )
    finance_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Correlation reference returned by the shared Finance Engine.",
    )
    finance_posted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_agriculture_operations",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_agriculture_operations",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        permissions = [
            (
                "approve_agricultureoperation",
                "Can approve or return agriculture operations",
            ),
            (
                "complete_agricultureoperation",
                "Can complete agriculture operations",
            ),
        ]
        indexes = [
            models.Index(
                fields=["operation_type", "status"],
                name="agri_operation_type_status_idx",
            ),
            models.Index(
                fields=["farm", "status"],
                name="agri_operation_farm_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(budget__gte=0),
                name="agri_operation_budget_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(actual_cost__gte=0),
                name="agri_operation_cost_nonnegative",
            ),
        ]

    @property
    def workflow_name(self):
        return self.WORKFLOW_NAME

    @property
    def business_unit(self):
        return self.BUSINESS_UNIT

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()

        if (
            self.planned_start_date
            and self.planned_end_date
            and self.planned_end_date < self.planned_start_date
        ):
            raise ValidationError(
                {"planned_end_date": "Planned end date cannot precede start date."}
            )

        if (
            self.actual_start_date
            and self.actual_end_date
            and self.actual_end_date < self.actual_start_date
        ):
            raise ValidationError(
                {"actual_end_date": "Actual end date cannot precede start date."}
            )

        if self.source_order_id:
            if getattr(self.source_order, "business_unit", "") != "AGRICULTURE":
                raise ValidationError(
                    {"source_order": "The source order must belong to Agriculture."}
                )

        if self.status == "CANCELLED" and not self.cancellation_reason.strip():
            raise ValidationError(
                {"cancellation_reason": "Cancellation requires a reason."}
            )

        if self.status == "COMPLETED" and not self.actual_end_date:
            raise ValidationError(
                {"actual_end_date": "A completed operation requires an end date."}
            )

    def __str__(self):
        return f"{self.code} - {self.get_operation_type_display()}"


class PoultryHouse(TimeStampedModel):
    HOUSE_TYPES = (
        ("BROODER", "Brooder House"),
        ("GROWER", "Grower House"),
        ("LAYER", "Layer House"),
        ("BROILER", "Broiler House"),
        ("BREEDER", "Breeder House"),
        ("QUARANTINE", "Quarantine House"),
        ("OTHER", "Other"),
    )

    farm = models.ForeignKey(
        PoultryFarm,
        on_delete=models.PROTECT,
        related_name="houses",
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=150)
    house_type = models.CharField(
        max_length=20,
        choices=HOUSE_TYPES,
        default="LAYER",
    )
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["farm__name", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["farm", "code"],
                name="agri_unique_house_code_per_farm",
            ),
        ]

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()

    def __str__(self):
        return f"{self.farm.code}/{self.code} - {self.name}"


class PoultryBreed(TimeStampedModel):
    BREED_TYPES = (
        ("LAYER", "Layer"),
        ("BROILER", "Broiler"),
        ("DUAL_PURPOSE", "Dual Purpose"),
        ("LOCAL", "Local / Indigenous"),
        ("BREEDER", "Breeder"),
    )

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120, unique=True)
    breed_type = models.CharField(max_length=20, choices=BREED_TYPES)
    expected_laying_age_weeks = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    expected_market_age_weeks = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()

    def __str__(self):
        return self.name


class PoultryFlock(TimeStampedModel):
    PURPOSES = (
        ("LAYERS", "Egg Layers"),
        ("BROILERS", "Meat / Broilers"),
        ("BREEDERS", "Breeding Stock"),
        ("DUAL_PURPOSE", "Dual Purpose"),
        ("CHICKS", "Chicks"),
    )

    STATUSES = (
        ("PLANNED", "Planned"),
        ("ACTIVE", "Active"),
        ("QUARANTINED", "Quarantined"),
        ("SOLD", "Sold"),
        ("CLOSED", "Closed"),
        ("CANCELLED", "Cancelled"),
    )

    SOURCES = (
        ("HATCHED", "Hatched Internally"),
        ("PURCHASED", "Purchased"),
        ("TRANSFERRED", "Transferred"),
        ("OTHER", "Other"),
    )

    code = models.CharField(max_length=40, unique=True)
    source_operation = models.ForeignKey(
        AgricultureOperation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_flocks",
        help_text="Approved Agriculture operation that created or acquired this flock.",
    )
    farm = models.ForeignKey(
        PoultryFarm,
        on_delete=models.PROTECT,
        related_name="flocks",
    )
    house = models.ForeignKey(
        PoultryHouse,
        on_delete=models.PROTECT,
        related_name="flocks",
    )
    breed = models.ForeignKey(
        PoultryBreed,
        on_delete=models.PROTECT,
        related_name="flocks",
    )
    purpose = models.CharField(max_length=20, choices=PURPOSES)
    source = models.CharField(
        max_length=20,
        choices=SOURCES,
        default="PURCHASED",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="PLANNED",
        db_index=True,
    )
    arrival_or_hatch_date = models.DateField()
    initial_quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    current_quantity = models.PositiveIntegerField(default=0)
    average_unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    livestock_product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="poultry_flocks",
        help_text="Shared Inventory livestock product representing birds in this flock.",
    )
    closed_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-arrival_or_hatch_date", "-pk"]
        indexes = [
            models.Index(
                fields=["farm", "status"],
                name="agri_flock_farm_status_idx",
            ),
            models.Index(
                fields=["purpose", "status"],
                name="agri_flock_purpose_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(initial_quantity__gt=0),
                name="agri_flock_initial_qty_positive",
            ),
            models.CheckConstraint(
                condition=Q(current_quantity__gte=0),
                name="agri_flock_current_qty_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(average_unit_cost__gte=0),
                name="agri_flock_unit_cost_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()

        if self.house_id and self.farm_id and self.house.farm_id != self.farm_id:
            raise ValidationError(
                {"house": "The poultry house must belong to the selected farm."}
            )

        if self.livestock_product_id:
            product = self.livestock_product
            if getattr(product, "business_unit", "") != "AGRICULTURE":
                raise ValidationError(
                    {"livestock_product": "The product must belong to Agriculture."}
                )
            if getattr(product, "product_type", "") != "LIVESTOCK":
                raise ValidationError(
                    {"livestock_product": "The product type must be Livestock."}
                )

        if self.status in {"SOLD", "CLOSED", "CANCELLED"} and not self.closed_at:
            raise ValidationError(
                {"closed_at": "A closed, sold or cancelled flock requires a closing date."}
            )

    def save(self, *args, **kwargs):
        if self._state.adding and not self.current_quantity:
            self.current_quantity = self.initial_quantity
        super().save(*args, **kwargs)

    @property
    def age_in_weeks(self):
        end_date = self.closed_at or timezone.localdate()
        return max((end_date - self.arrival_or_hatch_date).days // 7, 0)

    def __str__(self):
        return f"{self.code} ({self.current_quantity} birds)"


class DailyFlockRecord(TimeStampedModel):
    operation = models.ForeignKey(
        AgricultureOperation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="daily_flock_records",
    )
    flock = models.ForeignKey(
        PoultryFlock,
        on_delete=models.PROTECT,
        related_name="daily_records",
    )
    record_date = models.DateField(default=timezone.localdate)
    opening_quantity = models.PositiveIntegerField()
    additions = models.PositiveIntegerField(default=0)
    transferred_in = models.PositiveIntegerField(default=0)
    mortality = models.PositiveIntegerField(default=0)
    culls = models.PositiveIntegerField(default=0)
    sold = models.PositiveIntegerField(default=0)
    transferred_out = models.PositiveIntegerField(default=0)
    closing_quantity = models.PositiveIntegerField()
    average_weight_kg = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.000"))],
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="poultry_daily_records",
    )

    class Meta:
        ordering = ["-record_date", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["flock", "record_date"],
                name="agri_unique_daily_record_per_flock",
            ),
        ]

    @property
    def expected_closing_quantity(self):
        return (
            self.opening_quantity
            + self.additions
            + self.transferred_in
            - self.mortality
            - self.culls
            - self.sold
            - self.transferred_out
        )

    def clean(self):
        super().clean()
        expected = self.expected_closing_quantity
        if expected < 0:
            raise ValidationError(
                "Daily flock movements cannot produce a negative closing quantity."
            )
        if self.closing_quantity != expected:
            raise ValidationError(
                {
                    "closing_quantity": (
                        f"Closing quantity must be {expected} based on daily movements."
                    )
                }
            )

    def __str__(self):
        return f"{self.flock.code} - {self.record_date}"


class EggProduction(TimeStampedModel):
    operation = models.ForeignKey(
        AgricultureOperation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="egg_production_records",
    )
    flock = models.ForeignKey(
        PoultryFlock,
        on_delete=models.PROTECT,
        related_name="egg_production_records",
    )
    record_date = models.DateField(default=timezone.localdate)
    eggs_collected = models.PositiveIntegerField()
    saleable_eggs = models.PositiveIntegerField(default=0)
    hatching_eggs = models.PositiveIntegerField(default=0)
    cracked_eggs = models.PositiveIntegerField(default=0)
    dirty_or_rejected_eggs = models.PositiveIntegerField(default=0)
    inventory_product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="egg_production_records",
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="egg_production_records",
    )
    stock_movement = models.OneToOneField(
        "inventory.StockMovement",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="egg_production_record",
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="egg_production_records",
    )

    class Meta:
        ordering = ["-record_date", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["flock", "record_date"],
                name="agri_unique_egg_record_per_flock",
            ),
        ]

    @property
    def classified_eggs(self):
        return (
            self.saleable_eggs
            + self.hatching_eggs
            + self.cracked_eggs
            + self.dirty_or_rejected_eggs
        )

    @property
    def laying_rate(self):
        birds = self.flock.current_quantity
        if not birds:
            return Decimal("0.00")
        return (
            Decimal(self.eggs_collected) / Decimal(birds) * Decimal("100")
        ).quantize(Decimal("0.01"))

    def clean(self):
        super().clean()
        if self.flock_id and self.flock.purpose not in {
            "LAYERS",
            "BREEDERS",
            "DUAL_PURPOSE",
        }:
            raise ValidationError(
                {"flock": "Egg production requires a layer, breeder or dual-purpose flock."}
            )
        if self.classified_eggs != self.eggs_collected:
            raise ValidationError(
                {
                    "eggs_collected": (
                        "Collected eggs must equal saleable, hatching, cracked "
                        "and rejected eggs combined."
                    )
                }
            )

    def __str__(self):
        return f"{self.flock.code} - {self.eggs_collected} eggs"


class IncubationBatch(TimeStampedModel):
    STATUSES = (
        ("PLANNED", "Planned"),
        ("SET", "Eggs Set"),
        ("CANDLED", "Candled"),
        ("HATCHING", "Hatching"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )

    code = models.CharField(max_length=40, unique=True)
    operation = models.ForeignKey(
        AgricultureOperation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incubation_batches",
    )
    source_flock = models.ForeignKey(
        PoultryFlock,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incubation_batches",
    )
    incubator_asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incubation_batches",
    )
    eggs_set = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    set_date = models.DateField()
    expected_hatch_date = models.DateField()
    actual_hatch_date = models.DateField(null=True, blank=True)
    eggs_candled = models.PositiveIntegerField(default=0)
    fertile_eggs = models.PositiveIntegerField(default=0)
    infertile_eggs = models.PositiveIntegerField(default=0)
    chicks_hatched = models.PositiveIntegerField(default=0)
    unhatched_eggs = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="PLANNED",
        db_index=True,
    )
    chick_product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incubation_outputs",
    )
    output_warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incubation_outputs",
    )
    stock_movement = models.OneToOneField(
        "inventory.StockMovement",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incubation_output",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-set_date", "-pk"]

    @property
    def hatchability_rate(self):
        if not self.fertile_eggs:
            return Decimal("0.00")
        return (
            Decimal(self.chicks_hatched)
            / Decimal(self.fertile_eggs)
            * Decimal("100")
        ).quantize(Decimal("0.01"))

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()

        if self.expected_hatch_date < self.set_date:
            raise ValidationError(
                {"expected_hatch_date": "Expected hatch date cannot precede set date."}
            )
        if self.eggs_candled > self.eggs_set:
            raise ValidationError(
                {"eggs_candled": "Candled eggs cannot exceed eggs set."}
            )
        if self.fertile_eggs + self.infertile_eggs > self.eggs_candled:
            raise ValidationError(
                "Fertile and infertile eggs cannot exceed candled eggs."
            )
        if self.chicks_hatched > self.fertile_eggs:
            raise ValidationError(
                {"chicks_hatched": "Hatched chicks cannot exceed fertile eggs."}
            )
        if self.chicks_hatched + self.unhatched_eggs > self.eggs_set:
            raise ValidationError(
                "Hatched chicks and unhatched eggs cannot exceed eggs set."
            )
        if self.status == "COMPLETED" and not self.actual_hatch_date:
            raise ValidationError(
                {"actual_hatch_date": "A completed batch requires an actual hatch date."}
            )

    def __str__(self):
        return f"{self.code} - {self.eggs_set} eggs"


class FeedingRecord(TimeStampedModel):
    operation = models.ForeignKey(
        AgricultureOperation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="feeding_records",
    )
    flock = models.ForeignKey(
        PoultryFlock,
        on_delete=models.PROTECT,
        related_name="feeding_records",
    )
    record_date = models.DateField(default=timezone.localdate)
    feed_product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        related_name="poultry_feeding_records",
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="poultry_feeding_records",
    )
    quantity_kg = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    stock_movement = models.OneToOneField(
        "inventory.StockMovement",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="feeding_record",
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="poultry_feeding_records",
    )

    class Meta:
        ordering = ["-record_date", "-pk"]
        indexes = [
            models.Index(
                fields=["flock", "record_date"],
                name="agri_feed_flock_date_idx",
            ),
        ]

    @property
    def total_cost(self):
        return self.quantity_kg * self.unit_cost

    def clean(self):
        super().clean()
        if (
            self.feed_product_id
            and getattr(self.feed_product, "business_unit", "") != "AGRICULTURE"
        ):
            raise ValidationError(
                {"feed_product": "The feed product must belong to Agriculture."}
            )

    def __str__(self):
        return f"{self.flock.code} - {self.quantity_kg} kg"


class HealthRecord(TimeStampedModel):
    RECORD_TYPES = (
        ("VACCINATION", "Vaccination"),
        ("TREATMENT", "Treatment"),
        ("CHECKUP", "Routine Check-up"),
        ("BIOSECURITY", "Biosecurity"),
        ("OTHER", "Other"),
    )

    operation = models.ForeignKey(
        AgricultureOperation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="health_records",
    )
    flock = models.ForeignKey(
        PoultryFlock,
        on_delete=models.PROTECT,
        related_name="health_records",
    )
    record_date = models.DateField(default=timezone.localdate)
    record_type = models.CharField(max_length=20, choices=RECORD_TYPES)
    condition_or_vaccine = models.CharField(max_length=200)
    medicine_product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="poultry_health_records",
    )
    dosage = models.CharField(max_length=120, blank=True)
    birds_treated = models.PositiveIntegerField(default=0)
    next_due_date = models.DateField(null=True, blank=True)
    veterinarian_or_provider = models.CharField(max_length=150, blank=True)
    cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="poultry_health_records",
    )

    class Meta:
        ordering = ["-record_date", "-pk"]
        indexes = [
            models.Index(
                fields=["flock", "record_type", "record_date"],
                name="agri_health_type_date_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.next_due_date and self.next_due_date < self.record_date:
            raise ValidationError(
                {"next_due_date": "Next due date cannot precede the record date."}
            )
        if (
            self.flock_id
            and self.birds_treated > self.flock.current_quantity
        ):
            raise ValidationError(
                {"birds_treated": "Birds treated cannot exceed the current flock size."}
            )

    def __str__(self):
        return f"{self.flock.code} - {self.get_record_type_display()}"


class MortalityRecord(TimeStampedModel):
    CAUSES = (
        ("DISEASE", "Disease"),
        ("ACCIDENT", "Accident"),
        ("PREDATOR", "Predator"),
        ("HEAT_STRESS", "Heat Stress"),
        ("COLD_STRESS", "Cold Stress"),
        ("NUTRITION", "Nutrition"),
        ("UNKNOWN", "Unknown"),
        ("OTHER", "Other"),
    )

    operation = models.ForeignKey(
        AgricultureOperation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mortality_records",
    )
    flock = models.ForeignKey(
        PoultryFlock,
        on_delete=models.PROTECT,
        related_name="mortality_records",
    )
    record_date = models.DateField(default=timezone.localdate)
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    suspected_cause = models.CharField(
        max_length=20,
        choices=CAUSES,
        default="UNKNOWN",
    )
    health_record = models.ForeignKey(
        HealthRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mortality_records",
    )
    action_taken = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="poultry_mortality_records",
    )

    class Meta:
        ordering = ["-record_date", "-pk"]
        indexes = [
            models.Index(
                fields=["flock", "record_date"],
                name="agri_mortality_date_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.flock_id and self.quantity > self.flock.current_quantity:
            raise ValidationError(
                {"quantity": "Mortality cannot exceed the current flock size."}
            )
        if self.health_record_id and self.health_record.flock_id != self.flock_id:
            raise ValidationError(
                {"health_record": "The health record must belong to the same flock."}
            )

    def __str__(self):
        return f"{self.flock.code} - {self.quantity} mortality"
