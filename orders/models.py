from django.db import models
from django.conf import settings
from django.utils import timezone


class Order(models.Model):

    ORDER_TYPES = (
        ("ECOMMERCE", "Ecommerce Order"),
        ("CUSTOM_FURNITURE", "Custom Furniture Order"),
        ("RESTOCK", "Restock Existing Product"),
        ("NEW_PRODUCT", "New Product Development"),
        ("POS", "Point of Sale"),
    )

    STATUS = (
        ("DRAFT", "Draft"),
        ("PENDING", "Pending"),
        ("CONFIRMED", "Confirmed"),
        ("PROCESSING", "Processing"),
        ("IN_PRODUCTION", "In Production"),
        ("READY", "Ready"),
        ("DELIVERED", "Delivered"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )

    PAYMENT_STATUS = (
        ("UNPAID", "Unpaid"),
        ("PARTIAL", "Partial"),
        ("PAID", "Paid"),
        ("REFUNDED", "Refunded"),
    )

    DELIVERY_STATUS = (
        ("NOT_STARTED", "Not Started"),
        ("PENDING", "Pending"),
        ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"),
        ("FAILED", "Failed"),
    )

    order_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )
    

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    order_type = models.CharField(
        max_length=30,
        choices=ORDER_TYPES
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS,
        default="PENDING"
    )

    payment_status = models.CharField(
        max_length=30,
        choices=PAYMENT_STATUS,
        default="UNPAID"
    )

    delivery_status = models.CharField(
        max_length=30,
        choices=DELIVERY_STATUS,
        default="NOT_STARTED"
    )

    customer_name = models.CharField(max_length=200)

    customer_phone = models.CharField(max_length=50)

    customer_email = models.EmailField(
        blank=True,
        null=True
    )

    province = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    cell = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)

    delivery_address = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    expected_delivery_date = models.DateField(
        null=True,
        blank=True
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True
    )

    delivered_by = models.ForeignKey(
        "Employee.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivered_orders"
    )

    created_at = models.DateTimeField(default=timezone.now,editable=False)

    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):

        if not self.order_number:

            today = timezone.now().strftime("%Y%m%d")

            last_order = (
                Order.objects
                .filter(order_number__startswith=f"WPG-{today}")
                .order_by("-id")
                .first()
            )

            if last_order and last_order.order_number:

                last_number = int(
                    last_order.order_number.split("-")[-1]
                )

                next_number = last_number + 1

            else:

                next_number = 1

            self.order_number = f"WPG-{today}-{next_number:05d}"

        self.total_amount = (
            self.subtotal
            - self.discount
            + self.tax
        )

        super().save(*args, **kwargs)


    def __str__(self):

        return f"{self.order_number} - {self.customer_name}"

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    product_name = models.CharField(
        max_length=255,
        blank=True
    )

    quantity = models.PositiveIntegerField(default=1)

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(default=timezone.now,editable=False)


    @property
    def subtotal(self):

        return (self.quantity or 0) * (self.price or 0)


    def save(self, *args, **kwargs):

        if self.product and not self.product_name:

            self.product_name = self.product.name

        super().save(*args, **kwargs)


    def __str__(self):

        return f"{self.product_name} x {self.quantity}"