from django.db import models
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
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
    code = models.CharField(max_length=50, unique=True, blank=True)
    client_name = models.CharField(max_length=200)
    client_phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,default='planning')
    manager = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='construction_projects'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    # ======================================================
    # TOTAL SPENT
    # ======================================================
    @property
    def total_spent(self):
        materials = self.materials.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')
        labour = self.labours.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')
        expenses = self.expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        assets = self.asset_usage.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

        return materials + labour + expenses + assets


# ======================================================
# SITE
# ======================================================
class Site(models.Model):

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255, blank=True)
    supervisor = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_sites'
    )
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.project.name}"


# ======================================================
# TASK
# ======================================================
class Task(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

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

    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    progress = models.IntegerField(default=0)

    def __str__(self):
        return self.title


# ======================================================
# MATERIAL USAGE
# ======================================================
class ConstructionMaterial(models.Model):

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='materials')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)

    quantity_used = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)

    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total_cost = (self.quantity_used or 0) * (self.unit_cost or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project.name} - {self.raw_material.name}"


# ======================================================
# ASSET USAGE
# ======================================================
class ConstructionAssetUsage(models.Model):

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='asset_usage')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    hours_used = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_hour = models.DecimalField(max_digits=12, decimal_places=2)

    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total_cost = (self.hours_used or 0) * (self.cost_per_hour or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset.name} - {self.project.name}"


# ======================================================
# LABOUR
# ======================================================
class ConstructionLabour(models.Model):

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='labours')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    role = models.CharField(max_length=100)

    hours_worked = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2)

    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total_cost = (self.hours_worked or 0) * (self.hourly_rate or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.project.name}"


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

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenses')

    expense_type = models.CharField(max_length=50, choices=EXPENSE_TYPES)

    amount = models.DecimalField(max_digits=15, decimal_places=2)

    description = models.TextField(blank=True)

    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.name} - {self.expense_type}"