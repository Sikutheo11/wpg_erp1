import uuid
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from inventory.models import Product
from .payment_models import EcommercePayment
# Marketplace seller, commission and settlement models.
from .marketplace_models import (
    MarketplaceSeller,
    SellerProductAssignment,
    MarketplaceOrderLine,
    SellerSettlement,
    SellerSettlementLine,
)

from .payment_models import (
    EcommercePayment,
    PaymentProviderConfiguration,
)

class OnlineProduct(models.Model):
    """
    Ecommerce merchandising metadata for a shared Inventory Product.

    Product identity, business unit, product type, price, publication status,
    featured status and stock remain authoritative in inventory.Product.
    """

    ADD_TO_CART = "ADD_TO_CART"
    REQUEST_QUOTE = "REQUEST_QUOTE"
    MADE_TO_ORDER = "MADE_TO_ORDER"

    PURCHASE_MODES = (
        (ADD_TO_CART, "Add to Cart"),
        (REQUEST_QUOTE, "Request Quotation"),
        (MADE_TO_ORDER, "Made to Order"),
    )

    product = models.OneToOneField(
        Product,
        on_delete=models.PROTECT,
        related_name="online_product",
    )
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
    )
    title = models.CharField(
        max_length=200,
        blank=True,
    )
    image = models.ImageField(
        upload_to="ecommerce/products/",
        blank=True,
        null=True,
        help_text="Optional ecommerce hero image. Inventory image is the fallback.",
    )
    short_description = models.CharField(
        max_length=500,
        blank=True,
    )
    description = models.TextField(blank=True)
    purchase_mode = models.CharField(
        max_length=30,
        choices=PURCHASE_MODES,
        default=ADD_TO_CART,
        db_index=True,
    )
    minimum_order_quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    maximum_order_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    seo_title = models.CharField(
        max_length=200,
        blank=True,
    )
    seo_description = models.CharField(
        max_length=320,
        blank=True,
    )
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ["product__business_unit", "product__name"]
        indexes = [
            models.Index(
                fields=["purchase_mode"],
                name="ecom_online_mode_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.maximum_order_quantity is not None
            and self.maximum_order_quantity < self.minimum_order_quantity
        ):
            raise ValidationError(
                {
                    "maximum_order_quantity": (
                        "Maximum order quantity cannot be below "
                        "the minimum order quantity."
                    )
                }
            )

        if (
            self.purchase_mode == self.ADD_TO_CART
            and self.product_id
            and self.product.product_type in {"SERVICE", "CUSTOM"}
        ):
            raise ValidationError(
                {
                    "purchase_mode": (
                        "Service and custom products must use Request "
                        "Quotation or Made to Order."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title or self.product.name) or "product"
            candidate = base_slug
            suffix = 1

            while OnlineProduct.objects.exclude(pk=self.pk).filter(
                slug=candidate
            ).exists():
                suffix += 1
                candidate = f"{base_slug}-{suffix}"

            self.slug = candidate

        super().save(*args, **kwargs)

    @property
    def display_title(self):
        return self.title or self.product.name

    @property
    def selling_price(self):
        return self.product.selling_price

    @property
    def business_unit(self):
        return self.product.business_unit

    @property
    def is_published(self):
        return self.product.is_published

    @property
    def is_featured(self):
        return self.product.is_featured

    @property
    def display_image(self):
        return self.image or self.product.image

    @property
    def can_add_to_cart(self):
        return (
            self.purchase_mode == self.ADD_TO_CART
            and self.product.is_active
            and self.product.is_published
            and self.product.selling_price > Decimal("0.00")
        )

    def __str__(self):
        return self.display_title


class EcommerceCheckout(models.Model):
    """
    One customer checkout that may produce one Enterprise Order per business unit.
    """

    STATUSES = (
        ("PENDING", "Pending"),
        ("ORDERED", "Orders Created"),
        ("PARTIAL", "Partially Completed"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("FAILED", "Failed"),
    )

    checkout_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ecommerce_checkouts",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="PENDING",
        db_index=True,
    )
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=50)
    customer_email = models.EmailField(blank=True)
    province = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    cell = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    delivery_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default="RWF")
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["user", "status"],
                name="ecom_chk_user_status_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="ecom_chk_status_date_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=0),
                name="ecom_checkout_subtotal_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(discount__gte=0),
                name="ecom_checkout_discount_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(tax__gte=0),
                name="ecom_checkout_tax_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name="ecom_checkout_total_nonnegative",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.checkout_number:
            date_part = timezone.localdate().strftime("%Y%m%d")
            self.checkout_number = (
                f"CHK-{date_part}-{uuid.uuid4().hex[:8].upper()}"
            )

        self.total_amount = self.subtotal - self.discount + self.tax

        if self.status == "COMPLETED" and self.completed_at is None:
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.checkout_number} - {self.customer_name}"

    @property
    def customer_status(self):
        """Return one storefront status for all linked Enterprise Orders."""

        order_statuses = list(
            self.checkout_orders.values_list(
                "order__status",
                flat=True,
            )
        )

        if order_statuses and all(
            status == "CANCELLED"
            for status in order_statuses
        ):
            return {
                "code": "CANCELLED",
                "label": "Cancelled",
                "css_class": "bg-danger",
            }

        if "CANCELLED" in order_statuses:
            return {
                "code": "PARTIAL",
                "label": "Partially cancelled",
                "css_class": "bg-danger",
            }

        payment_confirmed = self.payments.filter(
            status="CONFIRMED"
        ).exists()

        if not payment_confirmed:
            return {
                "code": "AWAITING_PAYMENT",
                "label": "Awaiting payment",
                "css_class": "bg-secondary",
            }

        if not order_statuses:
            return {
                "code": "RECEIVED",
                "label": "Order received",
                "css_class": "bg-warning text-dark",
            }

        progress = {
            "DRAFT": 0,
            "PENDING": 0,
            "CONFIRMED": 1,
            "PROCESSING": 2,
            "IN_PRODUCTION": 2,
            "READY": 3,
            "DELIVERED": 4,
            "COMPLETED": 4,
        }

        lowest_progress = min(
            progress.get(status, 0)
            for status in order_statuses
        )

        statuses = {
            0: {
                "code": "RECEIVED",
                "label": "Order received",
                "css_class": "bg-warning text-dark",
            },
            1: {
                "code": "CONFIRMED",
                "label": "Confirmed",
                "css_class": "bg-info text-dark",
            },
            2: {
                "code": "PREPARING",
                "label": "Preparing",
                "css_class": "bg-primary",
            },
            3: {
                "code": "READY",
                "label": "Ready",
                "css_class": "bg-success",
            },
            4: {
                "code": "DELIVERED",
                "label": "Delivered",
                "css_class": "bg-success",
            },
        }

        return statuses[lowest_progress]


class EcommerceCheckoutOrder(models.Model):
    """
    Bridge between one Ecommerce checkout and its business-unit Orders.
    """

    BUSINESS_UNITS = Product.BUSINESS_UNITS

    checkout = models.ForeignKey(
        EcommerceCheckout,
        on_delete=models.CASCADE,
        related_name="checkout_orders",
    )
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="ecommerce_checkout_link",
    )
    business_unit = models.CharField(
        max_length=30,
        choices=BUSINESS_UNITS,
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["checkout_id", "business_unit"]
        constraints = [
            models.UniqueConstraint(
                fields=["checkout", "business_unit"],
                name="ecom_unique_order_per_unit",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="ecom_checkout_order_amount_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.order_id
            and self.business_unit
            and self.order.business_unit != self.business_unit
        ):
            raise ValidationError(
                {
                    "business_unit": (
                        "Checkout business unit must match the linked order."
                    )
                }
            )

    def __str__(self):
        return f"{self.checkout.checkout_number} / {self.order.order_number}"
