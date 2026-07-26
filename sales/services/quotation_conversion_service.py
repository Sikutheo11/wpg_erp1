from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine
from orders.models import OrderItem
from orders.services import OrderService

from ..models import SalesQuotation


class QuotationConversionService:
    """
    Convert an approved SalesQuotation into an enterprise Order.

    Responsibilities:
    - validate quotation eligibility;
    - prevent duplicate conversion;
    - create the Order through OrderService;
    - copy quotation items into OrderItem;
    - recalculate order totals;
    - link the quotation to the created order;
    - mark the quotation as converted.
    """

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
    def _validate_quotation(cls, quotation):
        if quotation is None:
            raise ValidationError(
                "Quotation is required."
            )

        if not isinstance(
            quotation,
            SalesQuotation,
        ):
            raise ValidationError(
                "A valid SalesQuotation instance is required."
            )

        if quotation.status != "approved":
            raise ValidationError(
                "Only approved quotations can be converted."
            )

        if quotation.converted_order_id:
            raise ValidationError(
                (
                    "This quotation has already been converted "
                    "into an order."
                )
            )

        if quotation.is_expired:
            raise ValidationError(
                "An expired quotation cannot be converted."
            )

        if not quotation.business_unit:
            raise ValidationError(
                "Quotation business unit is required."
            )

        if not quotation.order_type:
            raise ValidationError(
                "Quotation order type is required."
            )

        if not quotation.items.exists():
            raise ValidationError(
                (
                    "Add at least one quotation item "
                    "before conversion."
                )
            )

        if quotation.total_amount <= 0:
            raise ValidationError(
                (
                    "Quotation total must be greater "
                    "than zero."
                )
            )

        return quotation

    @staticmethod
    def _quantity_as_integer(quantity):
        """
        OrderItem.quantity is a PositiveIntegerField while quotation
        quantity is DecimalField. Only whole-number quantities can be
        converted safely.
        """

        quantity = Decimal(str(quantity))

        if quantity <= 0:
            raise ValidationError(
                "Item quantity must be greater than zero."
            )

        if quantity != quantity.to_integral_value():
            raise ValidationError(
                (
                    "Quotation item quantities must be whole numbers "
                    "before conversion to an order."
                )
            )

        return int(quantity)

    @classmethod
    @transaction.atomic
    def convert_to_order(
        cls,
        *,
        quotation,
        actor=None,
    ):
        quotation = (
            SalesQuotation.objects
            .select_for_update()
            .select_related(
                "customer",
                "customer__user",
            )
            .prefetch_related(
                "items__product",
            )
            .get(pk=quotation.pk)
        )

        cls._validate_quotation(
            quotation
        )

        customer = quotation.customer

        customer_name = cls._clean_text(
            customer.display_name
        )

        customer_phone = cls._clean_text(
            customer.phone
        )

        customer_email = cls._clean_text(
            customer.email
        )

        delivery_address = cls._clean_text(
            customer.address
        )

        notes_parts = []

        if quotation.notes:
            notes_parts.append(
                quotation.notes.strip()
            )

        notes_parts.append(
            (
                "Created from sales quotation "
                f"{quotation.quotation_no}."
            )
        )

        order = OrderService.create_order(
            business_unit=quotation.business_unit,
            order_type=quotation.order_type,
            user=(
                cls._user(actor)
                or customer.user
            ),
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            delivery_address=delivery_address,
            notes="\n".join(notes_parts),
            discount=quotation.discount,
            tax=quotation.tax,
            expected_delivery_date=None,
        )

        created_items = []

        for quotation_item in quotation.items.all():
            quantity = cls._quantity_as_integer(
                quotation_item.quantity
            )

            product_name = cls._clean_text(
                quotation_item.resolved_name
            )

            if not product_name:
                raise ValidationError(
                    (
                        "Every quotation item must have "
                        "a product or service name."
                    )
                )

            order_item = OrderItem.objects.create(
                order=order,
                product=quotation_item.product,
                product_name=product_name,
                quantity=quantity,
                price=quotation_item.unit_price,
                specifications=cls._clean_text(
                    quotation_item.specifications
                ),
            )

            created_items.append(
                order_item
            )

        OrderService.recalculate_totals(
            order
        )

        if order.subtotal != quotation.subtotal:
            raise ValidationError(
                (
                    "Order subtotal does not match quotation subtotal. "
                    "Review item quantities and prices."
                )
            )

        if order.total_amount != quotation.total_amount:
            raise ValidationError(
                (
                    "Order total does not match quotation total. "
                    "Review discount and tax values."
                )
            )

        quotation.status = "converted"
        quotation.converted_order = order
        quotation.converted_at = timezone.now()

        quotation.save(
            update_fields=[
                "status",
                "converted_order",
                "converted_at",
                "updated_at",
            ]
        )

        EventEngine.dispatch(
            event_code="SALES_QUOTATION_CONVERTED",
            actor=cls._user(actor),
            obj=quotation,
            title="Quotation Converted to Order",
            message=(
                f"Quotation {quotation.quotation_no} "
                f"was converted to order "
                f"{order.order_number}."
            ),
            level="SUCCESS",
            metadata={
                "quotation_id": quotation.pk,
                "quotation_no": quotation.quotation_no,
                "order_id": order.pk,
                "order_number": order.order_number,
                "business_unit": order.business_unit,
                "order_type": order.order_type,
                "item_ids": [
                    item.pk
                    for item in created_items
                ],
                "item_count": len(created_items),
                "subtotal": str(order.subtotal),
                "discount": str(order.discount),
                "tax": str(order.tax),
                "total_amount": str(order.total_amount),
                "converted_at": (
                    quotation.converted_at.isoformat()
                ),
            },
            notify_groups=[
                "Sales Manager",
                "Order Manager",
            ],
            notify_owner=True,
        )

        return {
            "quotation": quotation,
            "order": order,
            "items": created_items,
            "message": (
                f"Quotation {quotation.quotation_no} "
                f"converted to order "
                f"{order.order_number}."
            ),
        }
