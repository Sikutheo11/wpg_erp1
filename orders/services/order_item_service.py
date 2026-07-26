from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from core.event_engine import EventEngine

from ..models import OrderItem
from .order_service import OrderService


class OrderItemService:
    """
    Business logic for products, services, projects, and special requests
    added to enterprise orders.
    """

    EXISTING_PRODUCT_TYPES = {
        "ECOMMERCE",
        "POS",
        "RESTOCK",
    }

    CUSTOM_REQUEST_TYPES = {
        "CUSTOM_FURNITURE",
        "CUSTOM_ORDER",
        "PROJECT",
        "MAINTENANCE",
        "NEW_PRODUCT",
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
    def _product_price(product):
        """
        Return the selling price configured on the product.
        """

        if product is None:
            return Decimal("0.00")

        for field_name in (
            "selling_price",
            "sale_price",
            "unit_price",
            "price",
        ):
            value = getattr(product, field_name, None)

            if value is not None:
                return Decimal(str(value))

        return Decimal("0.00")

    @staticmethod
    def _product_name(product):
        if product is None:
            return ""

        return getattr(product, "name", None) or str(product)

    @classmethod
    def validate_product_business_unit(
        cls,
        *,
        order,
        product,
    ):
        """
        Ensure that the selected product belongs to the order business unit.
        Marketplace orders may contain products from all business units.
        """

        if product is None:
            return

        product_business_unit = getattr(product, "business_unit", None)

        if (
            order.business_unit != "MARKETPLACE"
            and product_business_unit
            and product_business_unit != order.business_unit
        ):
            raise ValidationError(
                "The selected product does not belong to this order's business unit."
            )

    @classmethod
    def validate_item_data(
        cls,
        *,
        order,
        product=None,
        product_name="",
        quantity=1,
        specifications="",
    ):
        if order is None:
            raise ValidationError("Order is required.")

        if order.status not in {"DRAFT", "PENDING"}:
            raise ValidationError(
                "Order items can only be changed while the order is draft or pending."
            )

        if quantity is None or quantity < 1:
            raise ValidationError("Quantity must be at least one.")

        product_name = (product_name or "").strip()
        specifications = (specifications or "").strip()

        if order.order_type in cls.EXISTING_PRODUCT_TYPES:
            if product is None:
                raise ValidationError("Select an existing product.")

        elif order.order_type in cls.CUSTOM_REQUEST_TYPES:
            if product is None and not product_name:
                raise ValidationError(
                    "Enter the requested product, service, or project name."
                )

            if not specifications:
                raise ValidationError(
                    "Specifications or scope of work are required for this order type."
                )

        elif product is None and not product_name:
            raise ValidationError(
                "Select a product or enter the requested item name."
            )

        cls.validate_product_business_unit(
            order=order,
            product=product,
        )

    @classmethod
    def resolve_item_price(
        cls,
        *,
        order,
        product=None,
        price=None,
    ):
        """
        Resolve unit selling price from product master data or quotation logic.
        """

        if order.order_type == "RESTOCK":
            return Decimal("0.00")

        if product is not None and order.order_type in {"ECOMMERCE", "POS"}:
            product_price = cls._product_price(product)

            if product_price < 0:
                raise ValidationError(
                    "Product selling price cannot be negative."
                )

            return product_price

        if order.order_type in cls.CUSTOM_REQUEST_TYPES:
            resolved_price = cls._decimal(price)

            if resolved_price < 0:
                raise ValidationError("Item price cannot be negative.")

            return resolved_price

        if product is not None:
            product_price = cls._product_price(product)

            if product_price < 0:
                raise ValidationError(
                    "Product selling price cannot be negative."
                )

            return product_price

        resolved_price = cls._decimal(price)

        if resolved_price < 0:
            raise ValidationError("Item price cannot be negative.")

        return resolved_price

    @classmethod
    @transaction.atomic
    def add_item(
        cls,
        *,
        order,
        product=None,
        product_name="",
        quantity=1,
        specifications="",
        price=None,
        actor=None,
    ):
        cls.validate_item_data(
            order=order,
            product=product,
            product_name=product_name,
            quantity=quantity,
            specifications=specifications,
        )

        resolved_name = (
            cls._product_name(product)
            if product is not None
            else (product_name or "").strip()
        )

        resolved_price = cls.resolve_item_price(
            order=order,
            product=product,
            price=price,
        )

        item = OrderItem.objects.create(
            order=order,
            product=product,
            product_name=resolved_name,
            quantity=quantity,
            price=resolved_price,
            specifications=(specifications or "").strip(),
        )

        OrderService.recalculate_totals(order)

        EventEngine.dispatch(
            event_code="ORDER_ITEM_ADDED",
            actor=cls._user(actor),
            obj=item,
            title="Order Item Added",
            message=(
                f"{item.product_name} was added to "
                f"order {order.order_number}."
            ),
            level="INFO",
            metadata={
                "order_id": order.pk,
                "order_item_id": item.pk,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": str(item.price),
                "subtotal": str(item.subtotal),
            },
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
        product_name="",
        quantity=None,
        specifications=None,
        price=None,
        actor=None,
    ):
        order = item.order

        if product is None:
            product = item.product

        if quantity is None:
            quantity = item.quantity

        if not product_name:
            product_name = item.product_name

        if specifications is None:
            specifications = item.specifications or ""

        cls.validate_item_data(
            order=order,
            product=product,
            product_name=product_name,
            quantity=quantity,
            specifications=specifications,
        )

        resolved_name = (
            cls._product_name(product)
            if product is not None
            else (product_name or "").strip()
        )

        resolved_price = cls.resolve_item_price(
            order=order,
            product=product,
            price=item.price if price is None else price,
        )

        item.product = product
        item.product_name = resolved_name
        item.quantity = quantity
        item.price = resolved_price
        item.specifications = (specifications or "").strip()

        item.save(
            update_fields=[
                "product",
                "product_name",
                "quantity",
                "price",
                "specifications",
            ]
        )

        OrderService.recalculate_totals(order)

        EventEngine.dispatch(
            event_code="ORDER_ITEM_UPDATED",
            actor=cls._user(actor),
            obj=item,
            title="Order Item Updated",
            message=(
                f"{item.product_name} was updated on "
                f"order {order.order_number}."
            ),
            level="INFO",
            metadata={
                "order_id": order.pk,
                "order_item_id": item.pk,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": str(item.price),
                "subtotal": str(item.subtotal),
            },
            notify_owner=True,
        )

        return item

    @classmethod
    @transaction.atomic
    def remove_item(
        cls,
        *,
        item,
        actor=None,
    ):
        order = item.order

        if order.status not in {"DRAFT", "PENDING"}:
            raise ValidationError(
                "Order items can only be removed while the order is draft or pending."
            )

        item_name = item.product_name
        item_id = item.pk

        item.delete()

        OrderService.recalculate_totals(order)

        EventEngine.dispatch(
            event_code="ORDER_ITEM_REMOVED",
            actor=cls._user(actor),
            obj=order,
            title="Order Item Removed",
            message=(
                f"{item_name} was removed from "
                f"order {order.order_number}."
            ),
            level="WARNING",
            metadata={
                "order_id": order.pk,
                "removed_order_item_id": item_id,
                "product_name": item_name,
            },
            notify_owner=True,
        )

        return order
