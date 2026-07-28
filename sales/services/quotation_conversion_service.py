from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine
from core.workflow_service import WorkflowService
from orders.models import OrderItem
from orders.services import OrderService

from ..models import SalesQuotation


class QuotationConversionService:
    """
    Convert an approved SalesQuotation into an enterprise Order.

    Responsibilities:
    - lock only the quotation database row;
    - validate quotation eligibility;
    - prevent duplicate conversion;
    - create the enterprise order through OrderService;
    - copy quotation items into OrderItem;
    - recalculate and verify order totals;
    - link the quotation to the created order;
    - move the quotation to the converted workflow step;
    - dispatch the conversion event.
    """

    WORKFLOW_CODE = "SALES_QUOTATION"
    CONVERTED_STEP = "converted"
    MONEY_QUANTIZER = Decimal("0.01")

    @staticmethod
    def _user(actor):
        """
        Return a User instance whether actor is a User or an
        Employee-like object containing a user attribute.
        """

        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(actor, "user", None)

    @staticmethod
    def _clean_text(value):
        return (value or "").strip()

    @classmethod
    def _money(cls, value):
        """
        Normalize monetary values to two decimal places.
        """

        return Decimal(str(value or 0)).quantize(
            cls.MONEY_QUANTIZER
        )

    @classmethod
    def _validate_quotation(
        cls,
        quotation,
        quotation_items=None,
    ):
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

        if quotation_items is None:
            has_items = quotation.items.exists()
        else:
            has_items = bool(quotation_items)

        if not has_items:
            raise ValidationError(
                (
                    "Add at least one quotation item "
                    "before conversion."
                )
            )

        if cls._money(quotation.total_amount) <= 0:
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
        quantity may be decimal. Only whole-number quantities can be
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
        if quotation is None or not getattr(
            quotation,
            "pk",
            None,
        ):
            raise ValidationError(
                "A saved quotation is required."
            )

        quotation_id = quotation.pk
        actor_user = cls._user(actor)

        # Important:
        # - use _base_manager to avoid custom manager joins;
        # - clear select_related joins;
        # - lock only the SalesQuotation row.
        #
        # This prevents PostgreSQL's:
        # "FOR UPDATE cannot be applied to the nullable side
        # of an outer join".
        quotation = (
            SalesQuotation._base_manager
            .select_related(None)
            .select_for_update(
                of=("self",)
            )
            .get(
                pk=quotation_id
            )
        )

        # Load quotation items separately after locking the quotation.
        quotation_items = list(
            quotation.items
            .select_related(
                "product"
            )
            .order_by(
                "pk"
            )
        )

        cls._validate_quotation(
            quotation,
            quotation_items=quotation_items,
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
                actor_user
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

        for quotation_item in quotation_items:
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

        if (
            cls._money(order.subtotal)
            != cls._money(quotation.subtotal)
        ):
            raise ValidationError(
                (
                    "Order subtotal does not match quotation subtotal. "
                    "Review item quantities and prices."
                )
            )

        if (
            cls._money(order.total_amount)
            != cls._money(quotation.total_amount)
        ):
            raise ValidationError(
                (
                    "Order total does not match quotation total. "
                    "Review discount and tax values."
                )
            )

        quotation.converted_order = order
        quotation.converted_at = timezone.now()

        quotation.save(
            update_fields=[
                "converted_order",
                "converted_at",
                "updated_at",
            ]
        )

        # Move approved -> converted through the Core Workflow Engine.
        # The detailed conversion event is dispatched below, therefore
        # dispatch_event=False prevents duplicate notifications/events.
        WorkflowService.move(
            obj=quotation,
            workflow_code=cls.WORKFLOW_CODE,
            to_step=cls.CONVERTED_STEP,
            user=actor_user,
            note=(
                f"Converted to enterprise order "
                f"{order.order_number}."
            ),
            dispatch_event=False,
        )

        EventEngine.dispatch(
            event_code="SALES_QUOTATION_CONVERTED",
            actor=actor_user,
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
                "subtotal": str(
                    cls._money(order.subtotal)
                ),
                "discount": str(
                    cls._money(order.discount)
                ),
                "tax": str(
                    cls._money(order.tax)
                ),
                "total_amount": str(
                    cls._money(order.total_amount)
                ),
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
