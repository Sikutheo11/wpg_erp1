from django.db import models
from django.utils import timezone
from accounts.models import User
from inventory.models import Product,Warehouse



# ==========================================
# CUSTOMER
# ==========================================

class Customer(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    company_name = models.CharField(
        max_length=200,
        blank=True
    )

    phone = models.CharField(
        max_length=30
    )

    address = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):

        if self.company_name:
            return self.company_name

        if self.user:
            return self.user.username

        return f"Customer-{self.id}"



# ==========================================
# SALES QUOTATION
# ==========================================

class SalesQuotation(models.Model):

    STATUS = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )


    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="quotations"
    )


    quotation_no = models.CharField(
        max_length=50,
        unique=True
    )


    quotation_date = models.DateField(
        default=timezone.now
    )


    valid_until = models.DateField()


    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="draft"
    )


    notes = models.TextField(
        blank=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.quotation_no



# ==========================================
# QUOTATION ITEMS
# ==========================================

class SalesQuotationItem(models.Model):

    quotation = models.ForeignKey(
        SalesQuotation,
        on_delete=models.CASCADE,
        related_name="items"
    )


    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )


    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    @property
    def subtotal(self):

        return self.quantity * self.unit_price



# ==========================================
# SALE
# ==========================================

class Sale(models.Model):

    STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )


    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="sales"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    quotation = models.ForeignKey(
        SalesQuotation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales"
    )


    sale_no = models.CharField(
        max_length=50,
        unique=True
    )


    sale_date = models.DateField(
        default=timezone.now
    )


    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending"
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):

        return self.sale_no



# ==========================================
# SALE ITEMS
# ==========================================

class SaleItem(models.Model):

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items"
    )


    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )


    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    @property
    def subtotal(self):

        return self.quantity * self.unit_price



# ==========================================
# INVOICE
# ==========================================

class Invoice(models.Model):

    STATUS = (
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    )


    sale = models.OneToOneField(
        Sale,
        on_delete=models.CASCADE,
        related_name="invoice"
    )


    invoice_no = models.CharField(
        max_length=50,
        unique=True
    )


    invoice_date = models.DateField(
        default=timezone.now
    )


    due_date = models.DateField()


    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    amount_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="unpaid"
    )


    @property
    def balance(self):

        return self.total_amount - self.amount_paid


    def __str__(self):

        return self.invoice_no



# ==========================================
# CUSTOMER PAYMENT
# ==========================================

class CustomerPayment(models.Model):


    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('mobile_money', 'Mobile Money'),
    )


    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments"
    )


    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS
    )


    payment_date = models.DateField(
        default=timezone.now
    )


    reference = models.CharField(
        max_length=100,
        blank=True
    )


    notes = models.TextField(
        blank=True
    )


    def __str__(self):

        return f"{self.invoice.invoice_no} - {self.amount}"