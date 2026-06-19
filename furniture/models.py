from django.db import models
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from Employee.models import Employee
from inventory.models import Product, RawMaterial, Asset



# ======================================================
# CUSTOMER / PRODUCTION ORDER
# ======================================================

class Order(models.Model):

    STATUS = [

        ('pending', 'Pending'),

        ('assigned', 'Assigned'),

        ('quotation_pending',
         'Quotation Pending'),

        ('quotation_approved',
         'Quotation Approved'),

        ('ongoing',
         'Ongoing'),

        ('completed',
         'Completed'),

        ('cancelled',
         'Cancelled'),

    ]


    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )


    customer_name = models.CharField(
        max_length=200
    )


    customer_phone = models.CharField(
        max_length=50,
        blank=True
    )


    quantity_to_produce = models.PositiveIntegerField()



    # Worker ukora quotation

    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_furniture_orders'
    )



    # Manager winjije order

    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_furniture_orders'
    )



    status = models.CharField(
        max_length=30,
        choices=STATUS,
        default='pending'
    )


    start_date = models.DateField(
        default=timezone.now
    )


    expected_end_date = models.DateField(
        null=True,
        blank=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )



    def __str__(self):

        return (
            f"{self.customer_name} - "
            f"{self.product.name}"
        )




# ======================================================
# BILL OF MATERIAL
# ======================================================

class BillOfMaterial(models.Model):


    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="boms"
    )


    raw_material = models.ForeignKey(
        RawMaterial,
        on_delete=models.CASCADE
    )


    quantity_required = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )



    @property
    def total_cost(self):

        return (
            self.quantity_required *
            self.raw_material.unit_cost
        )




# ======================================================
# QUOTATION
# Worker prepares
# Manager approves
# ======================================================

class Quotation(models.Model):


    STATUS = [

        ('draft','Draft'),

        ('submitted',
         'Submitted'),

        ('approved',
         'Approved'),

        ('rejected',
         'Rejected'),

    ]



    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="quotation"
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


    profit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    selling_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )



    status=models.CharField(
        max_length=20,
        choices=STATUS,
        default='draft'
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )



    @property
    def total_cost(self):

        return (
            self.material_cost +
            self.labour_cost +
            self.machine_cost
        )





# ======================================================
# PRODUCTION MATERIAL CONSUMPTION
# ======================================================

class ProductionMaterial(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="materials"
    )


    raw_material = models.ForeignKey(
        RawMaterial,
        on_delete=models.CASCADE
    )


    quantity_used=models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    unit_cost=models.DecimalField(
        max_digits=12,
        decimal_places=2
    )



    @property
    def total_cost(self):

        return (
            self.quantity_used *
            self.unit_cost
        )




# ======================================================
# LABOUR COST
# ======================================================

class ProductionLabour(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="labours"
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

        return (
            self.hours_worked *
            self.hourly_rate
        )


    def __str__(self):

        return f"{self.employee} - {self.order}" 
        
# ======================================================
# MACHINE COST
# ======================================================

class ProductionMachine(models.Model):


    order=models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="machines"
    )


    asset=models.ForeignKey(
        Asset,
        on_delete=models.PROTECT
    )


    hours_used=models.DecimalField(
        max_digits=10,
        decimal_places=2
    )


    hourly_cost=models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    @property
    def total_cost(self):

        return (
            self.hours_used *
            self.hourly_cost
        )




# ======================================================
# STOCK RESERVATION
# ======================================================

class StockReservation(models.Model):


    order=models.ForeignKey(
        Order,
        on_delete=models.CASCADE
    )


    raw_material=models.ForeignKey(
        RawMaterial,
        on_delete=models.CASCADE
    )


    quantity=models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    status=models.CharField(
        max_length=20,
        default="reserved"
    )





# ======================================================
# FINISHED PRODUCT OUTPUT
# ======================================================

class ProductionOutput(models.Model):


    order=models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="outputs"
    )


    product=models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )


    quantity_produced=models.PositiveIntegerField()


    produced_by=models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True
    )


    date=models.DateTimeField(
        auto_now_add=True
    )