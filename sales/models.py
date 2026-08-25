from decimal import Decimal
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from inventory.models import Product, Warehouse


class Customer(models.Model):
    CUSTOMER_TYPES = (
        ("INDIVIDUAL", "Individual"),
        ("COMPANY", "Company"),
        ("INSTITUTION", "Institution"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_customer_profile",
    )
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPES,
        default="INDIVIDUAL",
    )
    full_name = models.CharField(max_length=200, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    tax_number = models.CharField(max_length=100, blank=True)
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company_name", "full_name", "phone"]

    def clean(self):
        super().clean()

        if self.credit_limit < 0:
            raise ValidationError(
                {"credit_limit": "Credit limit cannot be negative."}
            )

        if not self.full_name and not self.company_name and not self.user:
            raise ValidationError(
                "Provide a full name, company name or linked user account."
            )

    @property
    def display_name(self):
        if self.company_name:
            return self.company_name

        if self.full_name:
            return self.full_name

        if self.user:
            full_name = getattr(self.user, "full_name", "")
            if callable(full_name):
                full_name = full_name()

            return full_name or getattr(self.user, "username", "") or str(
                self.user
            )

        return f"Customer-{self.pk or 'New'}"

    def __str__(self):
        return self.display_name


class SalesQuotation(models.Model):
    BUSINESS_UNITS = (
        ("FURNITURE", "Furniture & Manufacturing"),
        ("CONSTRUCTION", "Construction"),
        ("AGRICULTURE", "Agriculture / Poultry"),
        ("MARKETPLACE", "Marketplace"),
    )

    ORDER_TYPES = (
        ("ECOMMERCE", "Ecommerce"),
        ("CUSTOM_FURNITURE", "Custom Furniture"),
        ("RESTOCK", "Restock"),
        ("NEW_PRODUCT", "New Product Development"),
        ("POS", "Point of Sale"),
        ("PROJECT", "Construction Project"),
        ("CUSTOM_ORDER", "Custom Order"),
        ("MAINTENANCE", "Maintenance / Renovation"),
    )

    STATUS = (
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("converted", "Converted to Order"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="quotations",
    )
    quotation_no = models.CharField(max_length=50, unique=True)
    business_unit = models.CharField(
        max_length=30,
        choices=BUSINESS_UNITS,
        blank=True,
        default="",
    )
    order_type = models.CharField(
        max_length=30,
        choices=ORDER_TYPES,
        blank=True,
        default="",
    )
    quotation_date = models.DateField(default=timezone.localdate)
    valid_until = models.DateField()
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="draft",
    )
    notes = models.TextField(blank=True)
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotations_prepared",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotations_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    converted_order = models.OneToOneField(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_sales_quotation",
    )
    converted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            (
                "approve_salesquotation",
                "Can approve or reject sales quotations",
            ),
            (
                "convert_salesquotation",
                "Can convert sales quotations to orders",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.valid_until
            and self.quotation_date
            and self.valid_until < self.quotation_date
        ):
            raise ValidationError(
                {
                    "valid_until": (
                        "Valid-until date cannot be before quotation date."
                    )
                }
            )

        for field_name in ("subtotal", "discount", "tax", "total_amount"):
            value = getattr(self, field_name, Decimal("0.00"))

            if value < 0:
                raise ValidationError(
                    {
                        field_name: (
                            f"{field_name.replace('_', ' ').title()} "
                            "cannot be negative."
                        )
                    }
                )

        if self.discount > self.subtotal:
            raise ValidationError(
                {"discount": "Discount cannot exceed subtotal."}
            )

    @property
    def is_expired(self):
        return (
            self.valid_until
            and self.valid_until < timezone.localdate()
            and self.status not in {"approved", "converted", "cancelled"}
        )

    @property
    def balance_before_tax(self):
        return max(
            self.subtotal - self.discount,
            Decimal("0.00"),
        )

    def __str__(self):
        return self.quotation_no


class SalesQuotationItem(models.Model):
    quotation = models.ForeignKey(
        SalesQuotation,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_quotation_items",
    )
    product_name = models.CharField(max_length=200, blank=True)
    specifications = models.TextField(blank=True)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=1,
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pk"]

    def clean(self):
        super().clean()

        if self.quantity <= 0:
            raise ValidationError(
                {"quantity": "Quantity must be greater than zero."}
            )

        if self.unit_price < 0:
            raise ValidationError(
                {"unit_price": "Unit price cannot be negative."}
            )

        if not self.product and not self.product_name.strip():
            raise ValidationError(
                "Select an existing product or enter a custom item name."
            )

        if (
            self.product
            and self.quotation.business_unit
            and self.quotation.business_unit != "MARKETPLACE"
        ):
            product_business_unit = getattr(
                self.product,
                "business_unit",
                None,
            )

            if (
                product_business_unit
                and product_business_unit != self.quotation.business_unit
            ):
                raise ValidationError(
                    "The selected product does not belong to this business unit."
                )

    @property
    def resolved_name(self):
        if self.product:
            return getattr(self.product, "name", "") or str(self.product)

        return self.product_name

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.resolved_name} x {self.quantity}"


# LEGACY: new workflows must use orders.Order.
class Sale(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="sales",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    quotation = models.ForeignKey(
        SalesQuotation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legacy_sales",
    )
    sale_no = models.CharField(max_length=50, unique=True)
    sale_date = models.DateField(default=timezone.localdate)
    discount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    tax = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.sale_no


# LEGACY: new workflows must use orders.OrderItem.
class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


# LEGACY: new workflows must use finance.Receivable.
class Invoice(models.Model):
    STATUS = (
        ("unpaid", "Unpaid"),
        ("partial", "Partial"),
        ("paid", "Paid"),
    )

    sale = models.OneToOneField(
        Sale,
        on_delete=models.CASCADE,
        related_name="invoice",
    )
    invoice_no = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )
    amount_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="unpaid",
    )

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def __str__(self):
        return self.invoice_no


# LEGACY: new workflows must use finance.Payment.
class CustomerPayment(models.Model):
    PAYMENT_METHODS = (
        ("cash", "Cash"),
        ("bank", "Bank"),
        ("mobile_money", "Mobile Money"),
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
    )
    payment_date = models.DateField(default=timezone.localdate)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.invoice.invoice_no} - {self.amount}"


class EnterpriseInvoice(models.Model):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    VOID = "VOID"
    STATUS = (
        (DRAFT, "Draft"),
        (ISSUED, "Issued"),
        (PARTIAL, "Partially paid"),
        (PAID, "Paid"),
        (VOID, "Void"),
    )

    order = models.OneToOneField(
        "orders.Order", on_delete=models.PROTECT,
        related_name="sales_invoice",
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="enterprise_invoices",
    )
    receivable = models.OneToOneField(
        "finance.Receivable", on_delete=models.PROTECT,
        null=True, blank=True, related_name="sales_invoice",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default=DRAFT)
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="issued_sales_invoices",
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-invoice_date", "-pk"]
        permissions = [
            ("issue_enterpriseinvoice", "Can issue enterprise invoices"),
            ("send_enterpriseinvoice", "Can send enterprise invoices"),
            ("void_enterpriseinvoice", "Can void enterprise invoices"),
        ]

    @property
    def amount_paid(self):
        return self.receivable.amount_paid if self.receivable_id else Decimal("0.00")

    @property
    def balance(self):
        return max(self.total_amount - self.amount_paid, Decimal("0.00"))

    def __str__(self):
        return self.invoice_number


class InvoiceDelivery(models.Model):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    CHANNELS = ((EMAIL, "Email"), (WHATSAPP, "WhatsApp"))
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    STATUS = ((PENDING, "Pending"), (SENT, "Sent"), (FAILED, "Failed"))

    invoice = models.ForeignKey(
        EnterpriseInvoice, on_delete=models.CASCADE,
        related_name="deliveries",
    )
    channel = models.CharField(max_length=20, choices=CHANNELS)
    destination = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS, default=PENDING)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sent_sales_invoices",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
