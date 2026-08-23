from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from Employee.models import Employee
from inventory.models import Product, RawMaterial, Asset



class WorkCenter(models.Model):

    TYPES = (
        ("CUTTING", "Cutting"),
        ("ASSEMBLY", "Assembly"),
        ("SANDING", "Sanding"),
        ("PAINTING", "Painting"),
        ("UPHOLSTERY", "Upholstery"),
        ("PACKAGING", "Packaging"),
        ("CUSTOM", "Custom"),
    )

    name = models.CharField(
        max_length=120
    )

    code = models.CharField(
        max_length=30,
        unique=True
    )

    center_type = models.CharField(
        max_length=30,
        choices=TYPES
    )

    description = models.TextField(
        blank=True
    )

    capacity_per_day = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    working_hours_per_day = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8
    )

    efficiency = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

# ======================================================
# PRODUCTION JOB
# ======================================================

class ProductionJob(models.Model):

    JOB_TYPES = (
        ("RESTOCK", "Restock Existing Product"),
        ("CUSTOMER_CUSTOM", "Customer Custom Order"),
        ("NEW_PRODUCT", "New Product Development"),
        ("BACKORDER", "Ecommerce Backorder"),
    )

    STATUS = (
        ("QUOTATION", "Quotation"),
        ("APPROVED", "Approved"),
        ("ORDER_CONFIRMED", "Order Confirmed"),
        ("MATERIAL_RESERVED", "Material Reserved"),
        ("IN_PRODUCTION", "In Production"),
        ("QUALITY_CHECK", "Quality Check"),
        ("FINISHED_GOODS", "Finished Goods"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    )

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="production_job",
        null=True,
        blank=True
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    job_type = models.CharField(
        max_length=30,
        choices=JOB_TYPES,
        default="RESTOCK"
    )

    quantity_to_produce = models.PositiveIntegerField(default=1)

    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_production_jobs"
    )

    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_production_jobs"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS,
        default="QUOTATION"
    )

    description = models.TextField(blank=True)

    start_date = models.DateField(default=timezone.now)

    expected_end_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        if self.order:
            return f"{self.order} - Production Job"
        if self.product:
            return f"{self.product.name} - Production Job"
        return f"Production Job #{self.id}"

    @staticmethod
    def active_jobs():
        return ProductionJob.objects.exclude(
            status__in=[
                "FINISHED_GOODS",
                "DELIVERED",
                "CANCELLED",
            ]
        ).count()

    
    @staticmethod
    def completed_jobs():
        return ProductionJob.objects.filter(
            status__in=["FINISHED_GOODS", "DELIVERED"]
        ).count()


    @staticmethod
    def delayed_jobs():
        return ProductionJob.objects.filter(
            expected_end_date__lt=timezone.now().date()
        ).exclude(
            status__in=[
                "FINISHED_GOODS",
                "DELIVERED",
                "CANCELLED",
            ]
        ).count()


# ======================================================
# LEGACY FURNITURE ORDER
# Keep temporarily for old data safety
# ======================================================

class Order(models.Model):
    """
    LEGACY MODEL.
    New architecture uses orders.Order.
    Do not use this model for new workflows.
    """

    STATUS = (
        ("pending", "Pending"),
        ("assigned", "Assigned"),
        ("quotation_pending", "Quotation Pending"),
        ("quotation_approved", "Quotation Approved"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    customer_name = models.CharField(max_length=200)

    customer_phone = models.CharField(max_length=50, blank=True)

    quantity_to_produce = models.PositiveIntegerField()

    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_furniture_orders"
    )

    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_furniture_orders"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS,
        default="pending"
    )

    start_date = models.DateField(default=timezone.now)

    expected_end_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Legacy Furniture Order"
        verbose_name_plural = "Legacy Furniture Orders"

    def __str__(self):
        return f"{self.customer_name} - {self.product.name}"


# ======================================================
# BILL OF MATERIAL
# ======================================================

class BillOfMaterial(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="furniture_boms",
    )

    raw_material = models.ForeignKey(
        RawMaterial,
        on_delete=models.CASCADE,
        related_name="furniture_bom_items",
    )

    quantity_required = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    class Meta:
        ordering = [
            "product__name",
            "raw_material__name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "product",
                    "raw_material",
                ],
                name="unique_material_per_furniture_product",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "product",
                    "raw_material",
                ],
                name="furn_bom",
            ),
        ]

        verbose_name = "Bill of Material"
        verbose_name_plural = "Bills of Materials"

    def clean(self):
        errors = {}

        if self.product is None:
            errors["product"] = (
                "A product is required for a Bill of Material."
            )

        if self.quantity_required is not None:
            if self.quantity_required <= 0:
                errors["quantity_required"] = (
                    "Quantity required must be greater than zero."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()

        return super().save(*args, **kwargs)

    @property
    def unit_cost(self):
        if not self.raw_material:
            return 0

        return self.raw_material.unit_cost

    @property
    def total_cost(self):
        if not self.raw_material:
            return 0

        return (
            self.quantity_required
            * self.raw_material.unit_cost
        )

    def __str__(self):
        product_name = (
            self.product.name
            if self.product
            else "No Product"
        )

        material_name = (
            self.raw_material.name
            if self.raw_material
            else "No Material"
        )

        return (
            f"{product_name} - "
            f"{material_name} "
            f"({self.quantity_required})"
        )


# ======================================================
# QUOTATION
# ======================================================

class Quotation(models.Model):

    STATUS = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    production_job = models.OneToOneField(
        ProductionJob,
        on_delete=models.CASCADE,
        related_name="quotation",
        null=True,
        blank=True
    )

    prepared_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name="prepared_quotes"
    )

    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_quotes"
    )

    material_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    labour_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    machine_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    transport_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    other_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    profit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    profit_margin = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Optional margin percentage"
    )

    selling_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="DRAFT"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("approve_quotation", "Can approve furniture quotations"),
        ]

    @property
    def total_cost(self):
        return (
            self.material_cost
            + self.labour_cost
            + self.machine_cost
            + self.transport_cost
            + self.other_cost
        )

    @property
    def expected_selling_price(self):
        if self.selling_price:
            return self.selling_price
        return self.total_cost + self.profit

    def __str__(self):
        return f"Quotation #{self.id} - {self.status}"


# ======================================================
# PRODUCTION MATERIAL CONSUMPTION
# ======================================================

class ProductionMaterial(models.Model):

    production_job = models.ForeignKey(
        ProductionJob,
        on_delete=models.CASCADE,
        related_name="materials",
        null=True,
        blank=True
    )

    raw_material = models.ForeignKey(
        RawMaterial,
        on_delete=models.CASCADE
    )

    quantity_used = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    

    @property
    def total_cost(self):
        return self.quantity_used * self.unit_cost

    def __str__(self):
        return f"{self.raw_material} - {self.quantity_used}"


# ======================================================
# LABOUR COST
# ======================================================

class ProductionLabour(models.Model):

    production_job = models.ForeignKey(
        ProductionJob,
        on_delete=models.CASCADE,
        related_name="labours",
        null=True,
        blank=True
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE
    )

    hours_worked = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    hourly_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    @property
    def total_cost(self):
        return self.hours_worked * self.hourly_rate

    def __str__(self):
        return f"{self.employee} - {self.production_job}"


# ======================================================
# MACHINE COST
# ======================================================

class ProductionMachine(models.Model):

    production_job = models.ForeignKey(
        ProductionJob,
        on_delete=models.CASCADE,
        related_name="machines",
        null=True,
        blank=True
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT
    )

    hours_used = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    hourly_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    @property
    def total_cost(self):
        return self.hours_used * self.hourly_cost

    def __str__(self):
        return f"{self.asset} - {self.production_job}"


# ======================================================
# STOCK RESERVATION
# ======================================================

class StockReservation(models.Model):

    STATUS = (
        ("RESERVED", "Reserved"),
        ("USED", "Used"),
        ("RELEASED", "Released"),
        ("CANCELLED", "Cancelled"),
    )

    production_job = models.ForeignKey(
        ProductionJob,
        on_delete=models.CASCADE,
        related_name="stock_reservations",
        null=True,
        blank=True
    )

    raw_material = models.ForeignKey(
        RawMaterial,
        on_delete=models.CASCADE
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="RESERVED"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.raw_material} - {self.quantity}"


# ======================================================
# PRODUCTION ISSUE
# ======================================================

class ProductionIssue(models.Model):

    ISSUE_TYPES = (
        ("MATERIAL_SHORTAGE", "Material Shortage"),
        ("MACHINE_BREAKDOWN", "Machine Breakdown"),
        ("LABOUR_ABSENCE", "Labour Absence"),
        ("QUALITY_PROBLEM", "Quality Problem"),
        ("OTHER", "Other"),
    )

    SEVERITY = (
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    )

    production_job = models.ForeignKey(
        ProductionJob,
        on_delete=models.CASCADE,
        related_name="issues"
    )

    issue_type = models.CharField(
        max_length=50,
        choices=ISSUE_TYPES
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY,
        default="MEDIUM"
    )

    description = models.TextField()

    resolved = models.BooleanField(default=False)

    resolved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def mark_resolved(self, employee=None):
        self.resolved = True
        self.resolved_by = employee
        self.resolved_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.production_job} - {self.issue_type}"


# ======================================================
# PRODUCTION TIMELINE
# ======================================================

class ProductionTimeline(models.Model):

    production_job = models.ForeignKey(
        ProductionJob,
        on_delete=models.CASCADE,
        related_name="timeline"
    )

    action = models.CharField(max_length=150)

    from_status = models.CharField(
        max_length=50,
        blank=True
    )

    to_status = models.CharField(
        max_length=50,
        blank=True
    )

    performed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.production_job} - {self.action}"


# ======================================================
# FINISHED PRODUCT OUTPUT
# ======================================================

class ProductionOutput(models.Model):

    legacy_order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        related_name="outputs",
        null=True,
        blank=True,
        help_text=(
            "Legacy furniture order. "
            "Use production_job instead."
        ),
    )

    production_job = models.ForeignKey(
        ProductionJob,
        on_delete=models.CASCADE,
        related_name="outputs",
        null=True,
        blank=True,
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
    )

    quantity_produced = models.PositiveIntegerField()

    image = models.ImageField(
        upload_to="production_outputs/",
        null=True,
        blank=True,
    )

    produced_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    produced_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-produced_at"]

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.quantity_produced}"
        )

    def _get_production_job(self):
        return self.production_job

    @property
    def material_cost(self):
        if not self.production_job:
            return Decimal("0.00")

        from .services import ProductionCostService

        return ProductionCostService.material_cost(
            self.production_job
        )

    @property
    def labour_cost(self):
        if not self.production_job:
            return Decimal("0.00")

        from .services import ProductionCostService

        return ProductionCostService.labour_cost(
            self.production_job
        )

    @property
    def machine_cost(self):
        if not self.production_job:
            return Decimal("0.00")

        from .services import ProductionCostService

        return ProductionCostService.machine_cost(
            self.production_job
        )

    @property
    def total_cost(self):
        if not self.production_job:
            return Decimal("0.00")

        from .services import ProductionCostService

        return ProductionCostService.total_cost(
            self.production_job
        )

    @property
    def output_quantity(self):
        return Decimal(
            str(self.quantity_produced or 0)
        )

    @property
    def cost_per_unit(self):
        quantity = self.output_quantity

        if quantity <= 0:
            return Decimal("0.00")

        return (
            self.total_cost / quantity
        ).quantize(
            Decimal("0.01")
        )

    @property
    def profit_per_unit(self):
        if not self.production_job:
            return Decimal("0.00")

        from .services import ProductionCostService

        summary = ProductionCostService.job_cost_summary(
            production_job=self.production_job
        )

        return summary.get(
            "profit_per_unit",
            Decimal("0.00"),
        )

    @property
    def expected_profit(self):
        if not self.production_job:
            return Decimal("0.00")

        from .services import ProductionCostService

        summary = ProductionCostService.job_cost_summary(
            production_job=self.production_job
        )

        return summary.get(
            "expected_profit",
            Decimal("0.00"),
        )


# ======================================================
# PRODUCTION TASK
# ======================================================

class ProductionTask(models.Model):

    TASK_TYPES = (
        ("DESIGN", "Design"),
        ("MEASUREMENT", "Measurement"),
        ("CUTTING", "Cutting"),
        ("PLANING", "Planing"),
        ("THICKNESSING", "Thicknessing"),
        ("SHAPING", "Shaping"),
        ("JOINERY", "Joinery"),
        ("ASSEMBLY", "Assembly"),
        ("SANDING", "Sanding"),
        ("PAINTING", "Painting"),
        ("FINISHING", "Finishing"),
        ("DRYING", "Drying"),
        ("UPHOLSTERY", "Upholstery"),
        ("QUALITY_CHECK", "Quality Check"),
        ("PACKAGING", "Packaging"),
        ("DELIVERY", "Delivery"),
        ("OTHER", "Other"),
    )

    STATUS = (
        ("PENDING", "Pending"),
        ("READY", "Ready"),
        ("IN_PROGRESS", "In Progress"),
        ("PAUSED", "Paused"),
        ("BLOCKED", "Blocked"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )

    PRIORITY = (
        ("LOW", "Low"),
        ("NORMAL", "Normal"),
        ("HIGH", "High"),
        ("URGENT", "Urgent"),
    )

    production_job = models.ForeignKey(
        ProductionJob,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    work_center = models.ForeignKey(
        WorkCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks"
    )

    name = models.CharField(
        max_length=150,
    )

    task_type = models.CharField(
        max_length=30,
        choices=TASK_TYPES,
        default="OTHER",
    )

    description = models.TextField(
        blank=True,
    )

    sequence = models.PositiveIntegerField(
        default=1,
        help_text="Order of execution inside the production job.",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="PENDING",
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY,
        default="NORMAL",
    )

    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="production_tasks",
    )

    planned_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    actual_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    progress_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Task completion percentage from 0 to 100.",
    )

    planned_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    planned_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_production_tasks",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )
    

    class Meta:
        ordering = [
            "production_job",
            "sequence",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "production_job",
                    "sequence",
                ],
                name="unique_task_sequence_per_production_job",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "production_job",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "assigned_to",
                    "status",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.production_job} - "
            f"{self.sequence}. {self.name}"
        )

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.progress_percentage > 100:
            raise ValidationError(
                {
                    "progress_percentage": (
                        "Progress percentage cannot exceed 100."
                    )
                }
            )

        if (
            self.planned_start
            and self.planned_end
            and self.planned_end < self.planned_start
        ):
            raise ValidationError(
                {
                    "planned_end": (
                        "Planned end cannot be before planned start."
                    )
                }
            )

    @property
    def is_overdue(self):
        if not self.planned_end:
            return False

        if self.status in {
            "COMPLETED",
            "CANCELLED",
        }:
            return False

        return timezone.now() > self.planned_end

    @property
    def hours_variance(self):
        return self.actual_hours - self.planned_hours

    def start(self):
        if self.status not in {
            "PENDING",
            "READY",
            "PAUSED",
        }:
            return

        self.status = "IN_PROGRESS"

        if not self.started_at:
            self.started_at = timezone.now()

        self.save(
            update_fields=[
                "status",
                "started_at",
                "updated_at",
            ]
        )

    def complete(self):
        self.status = "COMPLETED"
        self.progress_percentage = 100
        self.completed_at = timezone.now()

        self.save(
            update_fields=[
                "status",
                "progress_percentage",
                "completed_at",
                "updated_at",
            ]
        )


# ======================================================
# TASK ASSIGNMENT HISTORY
# ======================================================

class ProductionTaskAssignment(models.Model):

    task = models.ForeignKey(
        ProductionTask,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="task_assignments",
    )

    assigned_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_task_records",
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    released_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    note = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "-assigned_at",
        ]

    def __str__(self):
        return f"{self.task} → {self.employee}"


# ======================================================
# TASK WORK LOG
# ======================================================

class ProductionTaskLog(models.Model):

    ACTIONS = (
        ("CREATED", "Created"),
        ("ASSIGNED", "Assigned"),
        ("STARTED", "Started"),
        ("PAUSED", "Paused"),
        ("RESUMED", "Resumed"),
        ("PROGRESS_UPDATED", "Progress Updated"),
        ("BLOCKED", "Blocked"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("NOTE", "Note"),
    )

    task = models.ForeignKey(
        ProductionTask,
        on_delete=models.CASCADE,
        related_name="logs",
    )

    action = models.CharField(
        max_length=30,
        choices=ACTIONS,
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="production_task_logs",
    )

    previous_status = models.CharField(
        max_length=20,
        blank=True,
    )

    new_status = models.CharField(
        max_length=20,
        blank=True,
    )

    hours_worked = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    progress_percentage = models.PositiveIntegerField(
        default=0,
    )

    note = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return f"{self.task} - {self.action}"


# ======================================================
# TASK CHECKLIST
# ======================================================

class ProductionChecklist(models.Model):

    task = models.ForeignKey(
        ProductionTask,
        on_delete=models.CASCADE,
        related_name="checklist_items",
    )

    title = models.CharField(
        max_length=200,
    )

    is_required = models.BooleanField(
        default=True,
    )

    is_completed = models.BooleanField(
        default=False,
    )

    completed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_task_checklists",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    note = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "order",
            "id",
        ]

    def __str__(self):
        return f"{self.task} - {self.title}"

    def mark_completed(self, employee=None):
        self.is_completed = True
        self.completed_by = employee
        self.completed_at = timezone.now()

        self.save(
            update_fields=[
                "is_completed",
                "completed_by",
                "completed_at",
            ]
        )


# ======================================================
# TASK MACHINE USAGE LOG
# ======================================================

class MachineUsageLog(models.Model):

    task = models.ForeignKey(
        ProductionTask,
        on_delete=models.CASCADE,
        related_name="machine_usage_logs",
    )

    machine = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="furniture_task_usage_logs",
    )

    operator = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="machine_usage_logs",
    )

    work_center = models.ForeignKey(
        WorkCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="machines"
    )

    started_at = models.DateTimeField()

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    hours_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    hourly_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    note = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-started_at",
        ]

    @property
    def total_cost(self):
        return self.hours_used * self.hourly_cost

    def __str__(self):
        return f"{self.task} - {self.machine}"


# ======================================================
# PRODUCTION TASK PROGRESS UPDATE
# ======================================================

class ProductionTaskProgress(models.Model):

    task = models.ForeignKey(
        ProductionTask,
        on_delete=models.CASCADE,
        related_name="progress_updates",
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_progress_updates",
    )

    progress_percentage = models.PositiveIntegerField()

    hours_worked = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    image = models.ImageField(
        upload_to="production_task_progress/%Y/%m/",
        null=True,
        blank=True,
    )

    note = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.progress_percentage > 100:
            raise ValidationError(
                {
                    "progress_percentage": (
                        "Progress percentage cannot exceed 100."
                    )
                }
            )

        if self.hours_worked < 0:
            raise ValidationError(
                {
                    "hours_worked": (
                        "Hours worked cannot be negative."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.task} - "
            f"{self.progress_percentage}%"
        )


class ProductionSettings(models.Model):
    """
    Furniture manufacturing costing and production settings.

    This model is designed as a singleton:
    only one active settings record should exist.
    """

    overhead_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("10.00"),
        help_text="Overhead percentage applied to direct production cost.",
    )

    wastage_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("5.00"),
        help_text="Default material wastage percentage.",
    )

    default_transport_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    default_other_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    default_labour_hourly_rate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    default_machine_hourly_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    vat_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("18.00"),
    )

    target_profit_margin = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("25.00"),
    )

    currency = models.CharField(
        max_length=10,
        default="RWF",
    )

    is_active = models.BooleanField(
        default=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Production Settings"
        verbose_name_plural = "Production Settings"

    def clean(self):
        errors = {}

        percentage_fields = {
            "overhead_rate": self.overhead_rate,
            "wastage_rate": self.wastage_rate,
            "vat_rate": self.vat_rate,
            "target_profit_margin": self.target_profit_margin,
        }

        for field_name, value in percentage_fields.items():
            if value is not None and value < 0:
                errors[field_name] = (
                    "Percentage values cannot be negative."
                )

        money_fields = {
            "default_transport_cost": self.default_transport_cost,
            "default_other_cost": self.default_other_cost,
            "default_labour_hourly_rate": (
                self.default_labour_hourly_rate
            ),
            "default_machine_hourly_cost": (
                self.default_machine_hourly_cost
            ),
        }

        for field_name, value in money_fields.items():
            if value is not None and value < 0:
                errors[field_name] = (
                    "Cost values cannot be negative."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.is_active:
            ProductionSettings.objects.exclude(
                pk=self.pk
            ).update(
                is_active=False
            )

        return super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        settings = cls.objects.filter(
            is_active=True
        ).first()

        if settings:
            return settings

        return cls.objects.create()

    def __str__(self):
        return f"Furniture Production Settings ({self.currency})"


class QualityInspection(models.Model):

    RESULT_CHOICES = (
        ("PENDING", "Pending"),
        ("PASSED", "Passed"),
        ("FAILED", "Failed"),
        ("CONDITIONAL", "Conditional Approval"),
    )

    INSPECTION_TYPES = (
        ("IN_PROCESS", "In-process Inspection"),
        ("FINAL", "Final Inspection"),
        ("RE_INSPECTION", "Re-inspection"),
    )

    production_job = models.ForeignKey(
        "ProductionJob",
        on_delete=models.CASCADE,
        related_name="quality_inspections",
    )

    inspection_type = models.CharField(
        max_length=20,
        choices=INSPECTION_TYPES,
        default="FINAL",
    )

    inspector = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quality_inspections",
    )

    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        default="PENDING",
    )

    passed = models.BooleanField(
        default=False,
    )

    score = models.PositiveIntegerField(
        default=0,
        help_text="Quality score between 0 and 100.",
    )

    quantity_inspected = models.PositiveIntegerField(
        default=0,
    )

    quantity_passed = models.PositiveIntegerField(
        default=0,
    )

    quantity_failed = models.PositiveIntegerField(
        default=0,
    )

    remarks = models.TextField(
        blank=True,
    )

    evidence_image = models.ImageField(
        upload_to="quality/inspections/%Y/%m/",
        null=True,
        blank=True,
    )

    approved_by = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_quality_inspections",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    inspected_at = models.DateTimeField(
        default=timezone.now,
    )

    created_at = models.DateTimeField(
        auto_now_add=True, null=True, blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True, null=True, blank=True
    )

    class Meta:
        ordering = ["-inspected_at"]
        permissions = [
            (
                "approve_qualityinspection",
                "Can approve furniture quality inspections",
            ),
        ]
        indexes = [
            models.Index(
                fields=["production_job", "result"],
                name="qual_job_result_idx",
            ),
        ]

    def clean(self):
        errors = {}

        if self.score > 100:
            errors["score"] = (
                "Quality score cannot exceed 100."
            )

        if self.quantity_passed > self.quantity_inspected:
            errors["quantity_passed"] = (
                "Passed quantity cannot exceed inspected quantity."
            )

        if self.quantity_failed > self.quantity_inspected:
            errors["quantity_failed"] = (
                "Failed quantity cannot exceed inspected quantity."
            )

        if (
            self.quantity_passed
            + self.quantity_failed
            > self.quantity_inspected
        ):
            errors["quantity_failed"] = (
                "Passed and failed quantities cannot exceed "
                "the inspected quantity."
            )

        if self.result == "PASSED" and self.quantity_failed > 0:
            errors["result"] = (
                "An inspection with failed units cannot be fully passed."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.passed = self.result == "PASSED"
        self.full_clean()

        return super().save(*args, **kwargs)

    def approve(self, employee):
        self.approved_by = employee
        self.approved_at = timezone.now()
        self.save(
            update_fields=[
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )

    def __str__(self):
        return (
            f"Inspection #{self.pk or 'New'} - "
            f"{self.production_job} - "
            f"{self.get_result_display()}"
        )

class ProductionDefect(models.Model):

    DEFECT_TYPES = (
        ("DIMENSION", "Incorrect Dimension"),
        ("MATERIAL", "Material Defect"),
        ("ASSEMBLY", "Assembly Defect"),
        ("SURFACE", "Surface Defect"),
        ("PAINT", "Painting / Finishing Defect"),
        ("STRUCTURAL", "Structural Defect"),
        ("PACKAGING", "Packaging Defect"),
        ("OTHER", "Other"),
    )

    SEVERITY_CHOICES = (
        ("MINOR", "Minor"),
        ("MAJOR", "Major"),
        ("CRITICAL", "Critical"),
    )

    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("REWORK_REQUIRED", "Rework Required"),
        ("UNDER_REWORK", "Under Rework"),
        ("RESOLVED", "Resolved"),
        ("ACCEPTED", "Accepted with Deviation"),
        ("SCRAPPED", "Scrapped"),
    )

    inspection = models.ForeignKey(
        QualityInspection,
        on_delete=models.CASCADE,
        related_name="defects",
    )

    production_job = models.ForeignKey(
        "ProductionJob",
        on_delete=models.CASCADE,
        related_name="quality_defects",
    )

    defect_type = models.CharField(
        max_length=30,
        choices=DEFECT_TYPES,
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="MINOR",
    )

    description = models.TextField()

    affected_quantity = models.PositiveIntegerField(
        default=1,
    )

    root_cause = models.TextField(
        blank=True,
    )

    corrective_action = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="OPEN",
    )

    evidence_image = models.ImageField(
        upload_to="quality/defects/%Y/%m/",
        null=True,
        blank=True,
    )

    reported_by = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_quality_defects",
    )

    resolved_by = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_quality_defects",
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True, null=True, blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True, null=True, blank=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "production_job",
                    "status",
                ],
                name="qual_defect_job_idx",
            ),
        ]

    def resolve(self, employee, corrective_action=""):
        self.status = "RESOLVED"
        self.resolved_by = employee
        self.resolved_at = timezone.now()

        if corrective_action:
            self.corrective_action = corrective_action

        self.save(
            update_fields=[
                "status",
                "resolved_by",
                "resolved_at",
                "corrective_action",
                "updated_at",
            ]
        )

    def __str__(self):
        return (
            f"{self.get_defect_type_display()} - "
            f"{self.production_job}"
        )

class ReworkOrder(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("ASSIGNED", "Assigned"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("VERIFIED", "Verified"),
        ("CANCELLED", "Cancelled"),
    )

    rework_code = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    production_job = models.ForeignKey(
        "ProductionJob",
        on_delete=models.CASCADE,
        related_name="rework_orders",
    )

    defect = models.ForeignKey(
        ProductionDefect,
        on_delete=models.CASCADE,
        related_name="rework_orders",
    )

    assigned_to = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_rework_orders",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    instructions = models.TextField()

    estimated_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    actual_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    rework_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    completion_note = models.TextField(
        blank=True,
    )

    completion_image = models.ImageField(
        upload_to="quality/rework/%Y/%m/",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_rework_orders",
    )

    completed_by = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_rework_orders",
    )

    created_at = models.DateTimeField(
        auto_now_add=True, null=True, blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True, null=True, blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("verify_reworkorder", "Can verify furniture rework orders"),
        ]

    def save(self, *args, **kwargs):
        if not self.rework_code:
            last_id = (
                ReworkOrder.objects
                .order_by("-id")
                .values_list("id", flat=True)
                .first()
                or 0
            )

            self.rework_code = (
                f"RWK-{timezone.now():%Y%m%d}-"
                f"{last_id + 1:05d}"
            )

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.rework_code


