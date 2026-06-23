from django.db import models
from django.utils import timezone
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from accounts.models import User
from Employee.models import Department, Employee
import random
import string
from django.utils.text import slugify


# =========================
# CATEGORY
# =========================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Warehouse(models.Model):

    name=models.CharField(
        max_length=100
    )

    location=models.CharField(
        max_length=200,
        blank=True
    )

    def __str__(self):
        return self.name


# =========================
# SUPPLIER
# =========================
class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# =========================
# RAW MATERIAL
# =========================
class RawMaterial(models.Model):

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('disposed', 'Disposed'),
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    category = models.ForeignKey(
    Category,
    on_delete=models.SET_NULL,
    null=True
    )
    name = models.CharField(max_length=200)

    code = models.CharField(
        max_length=50,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    unit = models.CharField(
        max_length=20,
        default='Kg'
    )

    minimum_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    def __str__(self):
        return self.name

    @property
    def current_stock(self):

        stock_in = StockMovement.objects.filter(
            raw_material=self,
            movement_type='IN'
        ).aggregate(total=Sum('quantity'))['total'] or 0

        stock_out = StockMovement.objects.filter(
            raw_material=self,
            movement_type='OUT'
        ).aggregate(total=Sum('quantity'))['total'] or 0

        return stock_in - stock_out

    @property
    def needs_restock(self):
        return self.current_stock <= self.minimum_stock


# =========================
# PRODUCT
# =========================
class Product(models.Model):

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    product_code = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20,default="pcs")
    selling_price = models.DecimalField(max_digits=12,decimal_places=2)
    reorder_level = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(default=timezone.now)
    slug = models.SlugField(unique=True, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    

    def save(self, *args, **kwargs):
        if not self.product_code:
            prefix = self.name[:3].upper()
            last_id = Product.objects.order_by('-id').first()
            next_id = 1

            if last_id:
                next_id = last_id.id + 1

            self.product_code = f"{prefix}-{next_id:05d}"

        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)


# =========================
# ASSET
# =========================
class Asset(models.Model):

    ASSET_TYPES = (
        ('machine', 'Machine'),
        ('vehicle', 'Vehicle'),
        ('computer', 'Computer'),
        ('tool', 'Tool'),
        ('furniture', 'Furniture'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
        ('disposed', 'Disposed'),
    )

    asset_type = models.CharField(
        max_length=50,
        choices=ASSET_TYPES
    )

    name = models.CharField(
        max_length=200
    )

    asset_code = models.CharField(
        max_length=100,
        unique=True,
        blank=True
    )

    purchase_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    purchase_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def generate_code(self):
        prefix = self.asset_type[:3].upper()
        random_part = ''.join(
            random.choices(
                string.ascii_uppercase +
                string.digits,
                k=6
            )
        )
        return f"{prefix}-{random_part}"

    def save(self, *args, **kwargs):

        if not self.asset_code:

            code = self.generate_code()

            while Asset.objects.filter(
                asset_code=code
            ).exists():

                code = self.generate_code()

            self.asset_code = code

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.asset_code})"


# =========================
# ASSET ASSIGNMENT
# =========================
class AssetAssignment(models.Model):

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    assigned_date = models.DateField()

    returned_date = models.DateField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.asset}"


# =========================
# STOCK MOVEMENT
# =========================
class StockMovement(models.Model):

    MOVEMENT_TYPES = (
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('TRANSFER', 'Transfer'),
        ('ADJUSTMENT', 'Adjustment'),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    raw_material = models.ForeignKey(
        RawMaterial,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPES
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    reference_no = models.CharField(
        max_length=100,
        blank=True
    )
    warehouse=models.ForeignKey(
    Warehouse,
    on_delete=models.CASCADE,
    null=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    def __str__(self):
        return f"{self.movement_type} - {self.quantity}"