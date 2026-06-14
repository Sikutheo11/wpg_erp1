from django.db import models
from Employee.models import Employee
from inventory.models import Product, RawMaterial


# =========================
# PRODUCTION ORDER
# =========================
class Order(models.Model):

    STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_to_produce = models.PositiveIntegerField()

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default='pending')

    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name="production_orders"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity_to_produce}"


# =========================
# MATERIALS USED IN PRODUCTION
# =========================
class ProductionMaterial(models.Model):

    production_order = models.ForeignKey(Order,
        on_delete=models.CASCADE,
        related_name='materials'
    )

    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)

    quantity_used = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def total_cost(self):
        return self.quantity_used * self.unit_cost

    def __str__(self):
        return f"{self.raw_material.name} ({self.production_order})"


# =========================
# PRODUCTION OUTPUT (FINISHED GOODS)
# =========================
class ProductionOutput(models.Model):

    production_order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='outputs'
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity_produced = models.PositiveIntegerField()

    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity_produced}"


# =========================
# LABOUR COST
# =========================
class ProductionLabour(models.Model):

    production_order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='labours'
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    hours_worked = models.DecimalField(max_digits=10, decimal_places=2)

    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def total_cost(self):
        return self.hours_worked * self.hourly_rate

    def __str__(self):
        return f"{self.employee} - {self.production_order}"

# ======================================================
# PRODUCTION MACHINE USAGE
# ======================================================
class ProductionMachine(models.Model):

    production_order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='machines'
    )

    asset = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='production_usage'
    )

    hours_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    hourly_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_cost(self):
        return (self.hours_used or 0) * (self.hourly_cost or 0)

    def __str__(self):
        return f"{self.asset.name} - {self.production_order}"

        
