from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from Employee.models import Employee
from inventory.models import Asset, Product, RawMaterial


ZERO = Decimal("0.00")


class ProductionPlan(models.Model):
    """
    Pre-production technical and financial plan.

    Estimated planning is intentionally separated from actual production
    consumption/costing.
    """

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("CALCULATED", "Calculated"),
        ("UNDER_REVIEW", "Under Review"),
        ("APPROVED", "Approved"),
        ("SUPERSEDED", "Superseded"),
    )

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="furniture_production_plan",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="furniture_production_plans",
    )
    name = models.CharField(max_length=200)
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("1.00"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    default_wastage_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    overhead_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    target_profit_margin = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Gross margin percentage on recommended selling price.",
    )

    material_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    labour_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    machine_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    additional_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    direct_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    overhead_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    estimated_total_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    estimated_cost_per_unit = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    recommended_selling_price = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    expected_profit = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )

    assumptions = models.TextField(blank=True)
    prepared_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prepared_production_plans",
    )
    reviewed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_production_plans",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "furniture"
        ordering = ["-created_at"]
        permissions = [
            ("approve_productionplan", "Can approve furniture production plans"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="furn_plan_quantity_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(default_wastage_rate__gte=0),
                name="furn_plan_wastage_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(overhead_rate__gte=0),
                name="furn_plan_overhead_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(target_profit_margin__gte=0)
                    & models.Q(target_profit_margin__lt=100)
                ),
                name="furn_plan_margin_between_0_100",
            ),
        ]

    def clean(self):
        errors = {}
        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = "Production quantity must be greater than zero."
        if self.default_wastage_rate is not None and self.default_wastage_rate < 0:
            errors["default_wastage_rate"] = "Wastage cannot be negative."
        if self.overhead_rate is not None and self.overhead_rate < 0:
            errors["overhead_rate"] = "Overhead cannot be negative."
        if self.target_profit_margin is not None and (
            self.target_profit_margin < 0
            or self.target_profit_margin >= 100
        ):
            errors["target_profit_margin"] = (
                "Target gross margin must be at least 0 and below 100."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} x {self.quantity}"


class ProductionPlanMaterial(models.Model):
    plan = models.ForeignKey(
        ProductionPlan,
        on_delete=models.CASCADE,
        related_name="materials",
    )
    raw_material = models.ForeignKey(
        RawMaterial,
        on_delete=models.PROTECT,
        related_name="production_plan_lines",
    )
    quantity_per_unit = models.DecimalField(max_digits=14, decimal_places=4)
    wastage_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Leave blank to use plan default wastage.",
    )
    unit_cost_snapshot = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    estimated_quantity = models.DecimalField(
        max_digits=18, decimal_places=4, default=ZERO, editable=False
    )
    estimated_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = "furniture"
        ordering = ["raw_material__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "raw_material"],
                name="unique_material_per_production_plan",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_per_unit__gt=0),
                name="furn_plan_material_qty_gt_zero",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(wastage_rate__isnull=True)
                    | models.Q(wastage_rate__gte=0)
                ),
                name="furn_plan_material_waste_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.plan} - {self.raw_material}"


class ProductionPlanLabour(models.Model):
    plan = models.ForeignKey(
        ProductionPlan,
        on_delete=models.CASCADE,
        related_name="labour_lines",
    )
    role_name = models.CharField(max_length=120)
    hours_per_unit = models.DecimalField(max_digits=12, decimal_places=4)
    hourly_rate = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO
    )
    estimated_hours = models.DecimalField(
        max_digits=18, decimal_places=4, default=ZERO, editable=False
    )
    estimated_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = "furniture"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hours_per_unit__gt=0),
                name="furn_plan_labour_hours_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(hourly_rate__gte=0),
                name="furn_plan_labour_rate_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.plan} - {self.role_name}"


class ProductionPlanMachine(models.Model):
    plan = models.ForeignKey(
        ProductionPlan,
        on_delete=models.CASCADE,
        related_name="machine_lines",
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="production_plan_lines",
    )
    hours_per_unit = models.DecimalField(max_digits=12, decimal_places=4)
    hourly_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO
    )
    estimated_hours = models.DecimalField(
        max_digits=18, decimal_places=4, default=ZERO, editable=False
    )
    estimated_cost = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO, editable=False
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = "furniture"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(hours_per_unit__gt=0),
                name="furn_plan_machine_hours_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(hourly_cost__gte=0),
                name="furn_plan_machine_cost_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.plan} - {self.asset}"


class ProductionPlanAdditionalCost(models.Model):
    COST_TYPES = (
        ("TRANSPORT", "Transport"),
        ("PACKAGING", "Packaging"),
        ("SUBCONTRACT", "Subcontract"),
        ("ENERGY", "Energy / Utilities"),
        ("OTHER", "Other"),
    )

    plan = models.ForeignKey(
        ProductionPlan,
        on_delete=models.CASCADE,
        related_name="additional_cost_lines",
    )
    cost_type = models.CharField(
        max_length=20,
        choices=COST_TYPES,
        default="OTHER",
    )
    description = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=ZERO
    )

    class Meta:
        app_label = "furniture"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="furn_plan_additional_cost_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.plan} - {self.description}"
