from django.db import models
from decimal import Decimal
from django.db.models import Max


class Sale(models.Model):

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    sale_code = models.CharField(max_length=50, unique=True, blank=True)
    customer_name = models.CharField(max_length=200, blank=True, null=True)

    sale_date = models.DateTimeField(auto_now_add=True)

    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_sale_code(self):
        last = Sale.objects.aggregate(Max('id'))['id__max'] or 0
        return f"SALE-{last + 1:05d}"

    def calculate_totals(self):
        self.subtotal = sum(item.total for item in self.items.all())
        self.total = self.subtotal - (self.discount or Decimal('0'))

    def save(self, *args, **kwargs):
        if not self.sale_code:
            self.sale_code = self.generate_sale_code()

        super().save(*args, **kwargs)

        # recalc AFTER save (important for items relation)
        self.calculate_totals()
        super().save(update_fields=['subtotal', 'total'])

    def __str__(self):
        return self.sale_code


class SaleItem(models.Model):

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)

    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

        # auto-update parent sale totals
        self.sale.calculate_totals()
        self.sale.save()

    