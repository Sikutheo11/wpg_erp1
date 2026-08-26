from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone

from core.event_engine import EventEngine

from ..models import Customer, SalesQuotation, SalesQuotationItem


class QuotationService:
    """Business logic for enterprise sales quotations."""

    EDITABLE_STATUSES = {"draft", "rejected"}
    CUSTOMER_QUOTATION_ORDER_TYPES = {
        "CUSTOM_FURNITURE",
        "PROJECT",
        "CUSTOM_ORDER",
        "MAINTENANCE",
    }

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0))

    @staticmethod
    def _user(actor):
        if actor is None:
            return None
        if hasattr(actor, "is_authenticated"):
            return actor
        return getattr(actor, "user", None)

    @staticmethod
    def _clean_text(value):
        return (value or "").strip()

    @classmethod
    def _validate_customer(cls, customer):
        if customer is None or not isinstance(customer, Customer):
            raise ValidationError("A valid customer is required.")
        if not customer.is_active:
            raise ValidationError("The selected customer is inactive.")
        return customer

    @classmethod
    def _validate_quotation(cls, quotation):
        if quotation is None or not isinstance(quotation, SalesQuotation):
            raise ValidationError("A valid quotation is required.")
        return quotation

    @classmethod
    def _validate_business_unit(cls, value):
        valid = {v for v, _ in SalesQuotation.BUSINESS_UNITS}
        if value not in valid:
            raise ValidationError("Invalid business unit.")
        return value

    @classmethod
    def _validate_order_type(cls, value):
        valid = cls.CUSTOMER_QUOTATION_ORDER_TYPES
        if value not in valid:
            raise ValidationError(
                "Customer quotations are not available for this order type."
            )
        return value

    @classmethod
    def _ensure_editable(cls, quotation):
        cls._validate_quotation(quotation)
        if quotation.status not in cls.EDITABLE_STATUSES:
            raise ValidationError(
                "Quotation can only be edited while draft or rejected."
            )
        if quotation.converted_order_id:
            raise ValidationError("A converted quotation cannot be modified.")
        if quotation.is_expired:
            raise ValidationError("This quotation has expired.")

    @classmethod
    def generate_quotation_number(cls):
        today = timezone.localdate()
        prefix = f"QTN-{today:%Y%m%d}-"
        last = (
            SalesQuotation.objects.filter(quotation_no__startswith=prefix)
            .order_by("-quotation_no")
            .first()
        )
        sequence = 0
        if last:
            try:
                sequence = int(last.quotation_no.rsplit("-", 1)[1])
            except (TypeError, ValueError, IndexError):
                sequence = 0
        return f"{prefix}{sequence + 1:05d}"

    @classmethod
    @transaction.atomic
    def create_quotation(
        cls,
        *,
        customer,
        business_unit,
        order_type,
        valid_until=None,
        discount=0,
        tax=0,
        notes="",
        prepared_by=None,
        quotation_date=None,
        actor=None,
    ):
        customer = cls._validate_customer(customer)
        business_unit = cls._validate_business_unit(business_unit)
        order_type = cls._validate_order_type(order_type)
        quotation_date = quotation_date or timezone.localdate()
        valid_until = valid_until or quotation_date + timedelta(days=30)
        discount = cls._decimal(discount)
        tax = cls._decimal(tax)

        if valid_until < quotation_date:
            raise ValidationError(
                "Valid-until date cannot be before quotation date."
            )
        if discount < 0 or tax < 0:
            raise ValidationError("Discount and tax cannot be negative.")

        quotation = SalesQuotation.objects.create(
            customer=customer,
            quotation_no=cls.generate_quotation_number(),
            business_unit=business_unit,
            order_type=order_type,
            quotation_date=quotation_date,
            valid_until=valid_until,
            subtotal=Decimal("0.00"),
            discount=discount,
            tax=tax,
            total_amount=Decimal("0.00"),
            status="draft",
            notes=cls._clean_text(notes),
            prepared_by=prepared_by or cls._user(actor),
        )
        quotation.full_clean()

        EventEngine.dispatch(
            event_code="SALES_QUOTATION_CREATED",
            actor=cls._user(actor),
            obj=quotation,
            title="Sales Quotation Created",
            message=f"Quotation {quotation.quotation_no} was created.",
            level="INFO",
            metadata={
                "quotation_id": quotation.pk,
                "quotation_no": quotation.quotation_no,
                "customer_id": quotation.customer_id,
                "business_unit": quotation.business_unit,
                "order_type": quotation.order_type,
            },
            notify_groups=["Sales Manager"],
            notify_owner=True,
        )
        return quotation

    @classmethod
    @transaction.atomic
    def create_from_order(cls, *, order, actor=None):
        if order.business_unit != "FURNITURE" or order.order_type != "CUSTOM_FURNITURE":
            raise ValidationError("Customer quotation is only available for Custom Furniture orders.")
        if order.customer_quotation_id:
            return order.customer_quotation

        customer = None
        if order.user_id:
            customer = Customer.objects.filter(user=order.user).first()
        if customer is None and order.customer_phone:
            customer = Customer.objects.filter(phone=order.customer_phone).first()
        if customer is None:
            customer = Customer.objects.create(
                user=order.user if order.user_id and not Customer.objects.filter(user=order.user).exists() else None,
                full_name=order.customer_name or "Furniture Customer",
                phone=order.customer_phone,
                email=order.customer_email or "",
                address=order.delivery_address or "",
            )

        quotation = cls.create_quotation(
            customer=customer,
            business_unit=order.business_unit,
            order_type=order.order_type,
            discount=order.discount,
            tax=order.tax,
            notes=f"Prepared from customer request {order.order_number}.",
            prepared_by=cls._user(actor),
            actor=actor,
        )
        for source in order.items.select_related("product"):
            SalesQuotationItem.objects.create(
                quotation=quotation,
                product=source.product,
                product_name=source.product_name,
                specifications=source.specifications,
                quantity=source.quantity,
                unit_price=Decimal("0.00"),
            )
        cls.recalculate_totals(quotation, actor=actor)
        order.customer_quotation = quotation
        order.status = "QUOTED"
        order.save(update_fields=["customer_quotation", "status", "updated_at"])
        return quotation

    @classmethod
    @transaction.atomic
    def recalculate_totals(cls, quotation, *, actor=None):
        quotation = cls._validate_quotation(quotation)
        expression = ExpressionWrapper(
            F("quantity") * F("unit_price"),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        subtotal = (
            quotation.items.aggregate(total=Sum(expression))["total"]
            or Decimal("0.00")
        )
        subtotal = cls._decimal(subtotal)
        discount = cls._decimal(quotation.discount)
        tax = cls._decimal(quotation.tax)

        if discount < 0 or tax < 0:
            raise ValidationError("Discount and tax cannot be negative.")
        if discount > subtotal:
            raise ValidationError("Discount cannot exceed quotation subtotal.")

        quotation.subtotal = subtotal
        quotation.total_amount = max(
            subtotal - discount + tax,
            Decimal("0.00"),
        )
        quotation.save(
            update_fields=["subtotal", "total_amount", "updated_at"]
        )
        return quotation

    @classmethod
    @transaction.atomic
    def add_item(
        cls,
        *,
        quotation,
        product=None,
        product_name="",
        specifications="",
        quantity=1,
        unit_price=None,
        actor=None,
    ):
        cls._ensure_editable(quotation)
        quantity = cls._decimal(quantity)
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        product_name = cls._clean_text(product_name)
        if product is None and not product_name:
            raise ValidationError(
                "Select an existing product or enter a custom item name."
            )

        resolved_name = product_name
        if product is not None:
            resolved_name = getattr(product, "name", "") or str(product)
            if unit_price is None:
                unit_price = getattr(product, "selling_price", 0)

        unit_price = cls._decimal(unit_price)
        if unit_price < 0:
            raise ValidationError("Unit price cannot be negative.")

        item = SalesQuotationItem.objects.create(
            quotation=quotation,
            product=product,
            product_name=resolved_name,
            specifications=cls._clean_text(specifications),
            quantity=quantity,
            unit_price=unit_price,
        )
        item.full_clean()
        cls.recalculate_totals(quotation, actor=actor)

        EventEngine.dispatch(
            event_code="SALES_QUOTATION_ITEM_ADDED",
            actor=cls._user(actor),
            obj=item,
            title="Quotation Item Added",
            message=f"{item.resolved_name} was added to {quotation.quotation_no}.",
            level="INFO",
            metadata={
                "quotation_id": quotation.pk,
                "quotation_item_id": item.pk,
                "product_id": item.product_id,
                "quantity": str(item.quantity),
                "unit_price": str(item.unit_price),
                "subtotal": str(item.subtotal),
            },
            notify_groups=["Sales Manager"],
            notify_owner=True,
        )
        return item

    @classmethod
    @transaction.atomic
    def update_item(
        cls,
        *,
        item,
        product=None,
        product_name=None,
        specifications=None,
        quantity=None,
        unit_price=None,
        actor=None,
    ):
        if item is None:
            raise ValidationError("Quotation item is required.")
        quotation = item.quotation
        cls._ensure_editable(quotation)

        if product is not None:
            item.product = product
            item.product_name = getattr(product, "name", "") or str(product)
        elif product_name is not None:
            item.product = None
            item.product_name = cls._clean_text(product_name)

        if specifications is not None:
            item.specifications = cls._clean_text(specifications)
        if quantity is not None:
            quantity = cls._decimal(quantity)
            if quantity <= 0:
                raise ValidationError("Quantity must be greater than zero.")
            item.quantity = quantity
        if unit_price is not None:
            unit_price = cls._decimal(unit_price)
            if unit_price < 0:
                raise ValidationError("Unit price cannot be negative.")
            item.unit_price = unit_price

        item.full_clean()
        item.save()
        cls.recalculate_totals(quotation, actor=actor)
        return item

    @classmethod
    @transaction.atomic
    def remove_item(cls, *, item, actor=None):
        if item is None:
            raise ValidationError("Quotation item is required.")
        quotation = item.quotation
        cls._ensure_editable(quotation)
        item_name = item.resolved_name
        item_id = item.pk
        item.delete()
        cls.recalculate_totals(quotation, actor=actor)

        EventEngine.dispatch(
            event_code="SALES_QUOTATION_ITEM_REMOVED",
            actor=cls._user(actor),
            obj=quotation,
            title="Quotation Item Removed",
            message=f"{item_name} was removed from {quotation.quotation_no}.",
            level="WARNING",
            metadata={
                "quotation_id": quotation.pk,
                "removed_item_id": item_id,
            },
            notify_groups=["Sales Manager"],
            notify_owner=True,
        )
        return quotation

    @classmethod
    @transaction.atomic
    def update_pricing(
        cls,
        *,
        quotation,
        discount=None,
        tax=None,
        actor=None,
    ):
        cls._ensure_editable(quotation)
        if discount is not None:
            quotation.discount = cls._decimal(discount)
        if tax is not None:
            quotation.tax = cls._decimal(tax)
        if quotation.discount < 0 or quotation.tax < 0:
            raise ValidationError("Discount and tax cannot be negative.")
        quotation.save(update_fields=["discount", "tax", "updated_at"])
        return cls.recalculate_totals(quotation, actor=actor)

    @classmethod
    @transaction.atomic
    def submit(cls, *, quotation, actor=None):
        cls._ensure_editable(quotation)
        if not quotation.items.exists():
            raise ValidationError(
                "Add at least one item before sending the quotation."
            )
        cls.recalculate_totals(quotation, actor=actor)
        if quotation.total_amount <= 0:
            raise ValidationError("Quotation total must be greater than zero.")

        quotation.status = "sent"
        quotation.save(update_fields=["status", "updated_at"])
        try:
            source_order = quotation.source_order_request
        except ObjectDoesNotExist:
            source_order = None
        if source_order is not None:
            source_order.status = "AWAITING_CUSTOMER_APPROVAL"
            source_order.save(update_fields=["status", "updated_at"])
        EventEngine.dispatch(
            event_code="SALES_QUOTATION_SENT",
            actor=cls._user(actor),
            obj=quotation,
            title="Quotation Sent",
            message=f"Quotation {quotation.quotation_no} was sent.",
            level="INFO",
            metadata={"quotation_id": quotation.pk},
            notify_groups=["Sales Manager"],
            notify_owner=True,
        )
        return quotation

    @classmethod
    @transaction.atomic
    def approve(cls, *, quotation, approved_by=None, actor=None):
        cls._validate_quotation(quotation)
        if quotation.status != "sent":
            raise ValidationError("Only sent quotations can be approved.")
        if quotation.is_expired:
            raise ValidationError("An expired quotation cannot be approved.")

        quotation.status = "approved"
        quotation.approved_by = approved_by or cls._user(actor)
        quotation.approved_at = timezone.now()
        quotation.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )
        try:
            source_order = quotation.source_order_request
        except ObjectDoesNotExist:
            source_order = None
        if source_order is not None:
            from orders.services.order_service import OrderService
            OrderService.authorize_for_production(
                order=source_order,
                actor=actor or approved_by,
                customer_quotation=quotation,
            )
        EventEngine.dispatch(
            event_code="SALES_QUOTATION_APPROVED",
            actor=cls._user(actor),
            obj=quotation,
            title="Quotation Approved",
            message=f"Quotation {quotation.quotation_no} was approved.",
            level="SUCCESS",
            metadata={"quotation_id": quotation.pk},
            notify_groups=["Sales Manager", "Order Manager"],
            notify_owner=True,
        )
        return quotation

    @classmethod
    @transaction.atomic
    def reject(cls, *, quotation, reason="", actor=None):
        cls._validate_quotation(quotation)
        if quotation.status not in {"sent", "approved"}:
            raise ValidationError(
                "Only sent or approved quotations can be rejected."
            )
        if quotation.converted_order_id:
            raise ValidationError("A converted quotation cannot be rejected.")

        reason = cls._clean_text(reason)
        quotation.status = "rejected"
        quotation.approved_by = None
        quotation.approved_at = None
        if reason:
            quotation.notes = (
                f"{quotation.notes}\n\nRejection reason: {reason}"
                if quotation.notes
                else f"Rejection reason: {reason}"
            )
        quotation.save(
            update_fields=[
                "status",
                "notes",
                "approved_by",
                "approved_at",
                "updated_at",
            ]
        )
        try:
            source_order = quotation.source_order_request
        except ObjectDoesNotExist:
            source_order = None
        if source_order is not None:
            source_order.status = "AWAITING_QUOTATION"
            source_order.save(update_fields=["status", "updated_at"])
        return quotation

    @classmethod
    @transaction.atomic
    def cancel(cls, *, quotation, reason="", actor=None):
        cls._validate_quotation(quotation)
        if quotation.status in {"converted", "cancelled"}:
            raise ValidationError(
                "Converted or cancelled quotations cannot be cancelled."
            )
        if quotation.converted_order_id:
            raise ValidationError("A converted quotation cannot be cancelled.")

        reason = cls._clean_text(reason)
        quotation.status = "cancelled"
        if reason:
            quotation.notes = (
                f"{quotation.notes}\n\nCancellation reason: {reason}"
                if quotation.notes
                else f"Cancellation reason: {reason}"
            )
        quotation.save(update_fields=["status", "notes", "updated_at"])
        return quotation

    @classmethod
    @transaction.atomic
    def mark_expired_quotations(cls, *, actor=None):
        quotations = list(
            SalesQuotation.objects.select_for_update().filter(
                valid_until__lt=timezone.localdate(),
                status__in=["draft", "sent", "rejected"],
            )
        )
        for quotation in quotations:
            quotation.status = "expired"
            quotation.save(update_fields=["status", "updated_at"])
        return quotations

    @classmethod
    @transaction.atomic
    def duplicate(
        cls,
        *,
        quotation,
        valid_until=None,
        prepared_by=None,
        actor=None,
    ):
        quotation = cls._validate_quotation(quotation)
        copied = cls.create_quotation(
            customer=quotation.customer,
            business_unit=quotation.business_unit,
            order_type=quotation.order_type,
            valid_until=valid_until,
            discount=quotation.discount,
            tax=quotation.tax,
            notes=quotation.notes,
            prepared_by=prepared_by or cls._user(actor),
            actor=actor,
        )
        for source in quotation.items.all():
            SalesQuotationItem.objects.create(
                quotation=copied,
                product=source.product,
                product_name=source.product_name,
                specifications=source.specifications,
                quantity=source.quantity,
                unit_price=source.unit_price,
            )
        cls.recalculate_totals(copied, actor=actor)
        return copied
