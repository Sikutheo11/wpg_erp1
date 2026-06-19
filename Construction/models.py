from django.db import models
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from Employee.models import Employee
from inventory.models import Asset, RawMaterial


# ======================================================
# PROJECT
# ======================================================

class Project(models.Model):

    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('ongoing', 'Ongoing'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('delayed', 'Delayed'),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True
    )
    client_name = models.CharField(max_length=200)
    client_phone = models.CharField(
        max_length=20,
        blank=True
    )
    location = models.CharField(
        max_length=255,
        blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True
    )
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planning'
    )
    manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='construction_projects'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    def save(self, *args, **kwargs):
        if not self.code:
            next_id = (
                Project.objects.count()
                + 1
            )
            self.code = (
                f"PRJ-{next_id:05d}"
            )
        super().save(
            *args,
            **kwargs
        )

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def total_spent(self):

        materials = (
            self.materials.aggregate(
                total=Sum('total_cost')
            )['total']
            or Decimal('0')
        )

        labour = (
            self.labours.aggregate(
                total=Sum('total_cost')
            )['total']
            or Decimal('0')
        )

        expenses = (
            self.expenses.aggregate(
                total=Sum('amount')
            )['total']
            or Decimal('0')
        )

        assets = (
            self.asset_usage.aggregate(
                total=Sum('total_cost')
            )['total']
            or Decimal('0')
        )

        return (
            materials +
            labour +
            expenses +
            assets
        )

    @property
    def remaining_budget(self):

        return (
            self.budget -
            self.total_spent
        )
    @property
    def progress_percentage(self):

        total_tasks = (
            self.tasks.count()
        )

        if total_tasks == 0:
            return 0

        completed_tasks = (
            self.tasks.filter(
                status='done'
            ).count()
        )
            # ======================================================
    # AUTOMATIC PROJECT PROGRESS
    # ======================================================

    @property
    def progress_percentage(self):

        total_tasks = self.tasks.count()


        # Nta task irimo
        if total_tasks == 0:

            return 0


        total_progress = (
            self.tasks.aggregate(
                total=Sum('progress')
            )['total']
            or 0
        )


        return round(
            total_progress / total_tasks
        )


# ======================================================
# SITE
# ======================================================

class Site(models.Model):

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='sites'
    )

    name = models.CharField(
        max_length=200
    )

    location = models.CharField(
        max_length=255,
        blank=True
    )

    supervisor = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_sites'
    )

    start_date = models.DateField()

    expected_end_date = models.DateField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"{self.name}"
            f" - "
            f"{self.project.name}"
        )


# ======================================================
# TASK
# ======================================================

class Task(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks'
    )

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    title = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    start_date = models.DateField(
        null=True,
        blank=True
    )

    due_date = models.DateField(
        null=True,
        blank=True
    )

    progress = models.PositiveIntegerField(
        default=0
    )

    def __str__(self):
        return self.title


# ======================================================
# MATERIAL USAGE
# ======================================================

# ======================================================
# MATERIAL USAGE
# ======================================================

class ConstructionMaterial(models.Model):

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='materials'
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

    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    date = models.DateTimeField(
        auto_now_add=True
    )


    def save(self, *args, **kwargs):

        # Kubara cost
        self.total_cost = (
            self.quantity_used *
            self.unit_cost
        )


        # Kumenya niba ari record nshya
        is_new = self.pk is None


        # Kubanza kubika Material Usage
        super().save(
            *args,
            **kwargs
        )


        # Niba ari ubwa mbere tuyikuyemo stock
        if is_new:

            StockMovement.objects.create(

                raw_material=self.raw_material,

                movement_type='OUT',

                quantity=self.quantity_used,

                unit_cost=self.unit_cost,

                reference_no=(
                    f"PROJECT-{self.project.code}"
                )

            )


    def __str__(self):

        return (
            f"{self.project.name} - "
            f"{self.raw_material.name}"
        )


# ======================================================
# ASSET USAGE
# ======================================================

class ConstructionAssetUsage(models.Model):

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='asset_usage'
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE
    )

    hours_used = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    cost_per_hour = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    def save(self, *args, **kwargs):

        self.total_cost = (
            self.hours_used *
            self.cost_per_hour
        )

        super().save(
            *args,
            **kwargs
        )

    def __str__(self):
        return (
            f"{self.asset.name}"
            f" - "
            f"{self.project.name}"
        )


# ======================================================
# LABOUR
# ======================================================

class ConstructionLabour(models.Model):

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='labours'
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=100
    )

    hours_worked = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    hourly_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    def save(self, *args, **kwargs):

        self.total_cost = (
            self.hours_worked *
            self.hourly_rate
        )

        super().save(
            *args,
            **kwargs
        )

    def __str__(self):
        return (
            f"{self.employee}"
            f" - "
            f"{self.project.name}"
        )


# ======================================================
# EXPENSE
# ======================================================

class ConstructionExpense(models.Model):

    EXPENSE_TYPES = [
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('equipment', 'Equipment'),
        ('transport', 'Transport'),
        ('other', 'Other'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='expenses'
    )

    expense_type = models.CharField(
        max_length=50,
        choices=EXPENSE_TYPES
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    description = models.TextField(
        blank=True
    )

    date = models.DateTimeField(
        default=timezone.now
    )

    def __str__(self):

        return (
            f"{self.project.name}"
            f" - "
            f"{self.expense_type}"
        )