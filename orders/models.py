from django.db import models
from django.conf import settings
from django.utils import timezone
from furniture.models import Product
from core.file_validators import (
    validate_business_document,
    validate_image_upload,
)


class Order(models.Model):
    ORDER_TYPES = (
        ("ECOMMERCE", "Ecommerce Order"),
        ("CUSTOM_FURNITURE", "Custom Furniture Order"),
        ("CUSTOM_ORDER", "Custom Order"),
        ("RESTOCK", "Restock Existing Product"),
        ("NEW_PRODUCT", "New Product Development"),
        ("POS", "Point of Sale"),
        ("PROJECT", "Project / Contract Order"),
        ("MAINTENANCE", "Renovation / Maintenance Order"),
    )

    STATUS = (
        ("DRAFT", "Draft"),
        ("PENDING", "Pending"),
        ("AWAITING_QUOTATION", "Awaiting Quotation / Costing"),
        ("QUOTED", "Quotation Prepared"),
        ("AWAITING_CUSTOMER_APPROVAL", "Awaiting Customer Approval"),
        ("READY_FOR_PRODUCTION", "Ready for Production"),
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
    BUSINESS_UNITS = (
        ("FURNITURE", "Furniture & Manufacturing"),
        ("CONSTRUCTION", "Construction"),
        ("AGRICULTURE", "Agriculture / Poultry"),
        ("MARKETPLACE", "Marketplace"),
    )
    business_unit = models.CharField(
        max_length=30,
        choices=BUSINESS_UNITS,
        default="FURNITURE",
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

    customer_quotation = models.OneToOneField(
        "sales.SalesQuotation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_order_request",
    )

    production_costing = models.OneToOneField(
        "furniture.Quotation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_order_request",
    )

    production_authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="production_authorized_orders",
    )
    production_authorized_at = models.DateTimeField(null=True, blank=True)

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

    class Meta:
        permissions = [
            (
                "approve_order",
                "Can confirm or cancel enterprise orders",
            ),
            (
                "fulfil_order",
                "Can process and deliver enterprise orders",
            ),
        ]


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

    @property
    def requires_customer_quotation(self):
        return self.order_type == "CUSTOM_FURNITURE"

    @property
    def requires_internal_costing(self):
        return self.order_type in {"RESTOCK", "NEW_PRODUCT"}

    @property
    def is_production_authorized(self):
        return (
            self.business_unit == "FURNITURE"
            and self.status == "READY_FOR_PRODUCTION"
            and self.production_authorized_at is not None
        )

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    product_name = models.CharField(
        max_length=255,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    specifications = models.TextField(
        blank=True,
        help_text=(
            "Dimensions, materials, colour, design, location "
            "or other customer requirements."
        ),
    )

    reference_image = models.ImageField(
        upload_to="orders/reference_images/%Y/%m/",
        null=True,
        blank=True,
        validators=[validate_image_upload],
        help_text="Customer reference photo or existing product photo.",
    )

    design_attachment = models.FileField(
        upload_to="orders/design_attachments/%Y/%m/",
        null=True,
        blank=True,
        validators=[validate_business_document],
        help_text="Drawing, design, specification sheet, or supporting document.",
    )

    length_cm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    width_cm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    height_cm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    material_preference = models.CharField(max_length=200, blank=True)
    colour = models.CharField(max_length=100, blank=True)
    finish = models.CharField(max_length=100, blank=True)
    customer_budget = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    @property
    def subtotal(self):
        return self.quantity * self.price

    def __str__(self):
        return (
            f"{self.product_name} "
            f"x {self.quantity}"
        )
