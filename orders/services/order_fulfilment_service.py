from django.core.exceptions import ValidationError
from django.db import transaction

from core.event_engine import EventEngine
from inventory.models import Warehouse
from inventory.services import ReservationService

from .order_service import OrderService


class OrderFulfilmentService:
    """
    Handles inventory fulfilment for confirmed catalogue-product orders.
    """

    FULFILMENT_ORDER_TYPES = {
        "ECOMMERCE",
        "POS",
    }

    @staticmethod
    def _user(actor):
        if actor is None:
            return None
        if hasattr(actor, "is_authenticated"):
            return actor
        return getattr(actor, "user", None)

    @classmethod
    def _validate_order(cls, order):
        if order is None:
            raise ValidationError("Order is required.")

        if order.order_type not in cls.FULFILMENT_ORDER_TYPES:
            raise ValidationError(
                "Inventory fulfilment is only available for Ecommerce and POS orders."
            )

        if order.status not in {"CONFIRMED", "PROCESSING"}:
            raise ValidationError(
                "Only confirmed or processing orders can enter inventory fulfilment."
            )

        if not order.items.exists():
            raise ValidationError("The order must have at least one item.")

        if order.items.filter(product__isnull=True).exists():
            raise ValidationError(
                "This order contains a custom item without a catalogue product."
            )

    @staticmethod
    def _default_warehouse():
        warehouse = Warehouse.objects.order_by("id").first()

        if warehouse is None:
            raise ValidationError("No warehouse has been configured.")

        return warehouse

    @staticmethod
    def _supports_waiting_stock(order):
        status_field = order._meta.get_field("status")
        valid_statuses = {
            value
            for value, label in status_field.choices
        }
        return "WAITING_STOCK" in valid_statuses

    @classmethod
    @transaction.atomic
    def fulfil_order(
        cls,
        *,
        order,
        warehouse=None,
        actor=None,
    ):
        cls._validate_order(order)

        warehouse = warehouse or cls._default_warehouse()

        result = ReservationService.reserve_order(
            order=order,
            warehouse=warehouse,
            actor=actor,
        )

        reservations = result["reservations"]
        all_reserved = result["all_reserved"]

        if all_reserved:
            OrderService.mark_ready(
                order=order,
                actor=actor,
            )

            route_status = "READY"
            message = (
                f"All stock for order {order.order_number} was reserved successfully. "
                "The order is ready."
            )
            level = "SUCCESS"

        else:
            if cls._supports_waiting_stock(order):
                order.status = "WAITING_STOCK"
                order.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )
                route_status = "WAITING_STOCK"
            else:
                route_status = "CONFIRMED"

            message = (
                f"Order {order.order_number} could not be fully reserved "
                "and requires stock follow-up."
            )
            level = "WARNING"

        shortages = []

        for reservation in reservations:
            shortage = (
                reservation.requested_quantity
                - reservation.reserved_quantity
            )

            if shortage > 0:
                shortages.append(
                    {
                        "reservation_id": reservation.pk,
                        "order_item_id": reservation.order_item_id,
                        "product_id": reservation.product_id,
                        "product_name": reservation.product.name,
                        "requested_quantity": reservation.requested_quantity,
                        "reserved_quantity": reservation.reserved_quantity,
                        "shortage_quantity": shortage,
                        "status": reservation.status,
                    }
                )

        EventEngine.dispatch(
            event_code="ORDER_INVENTORY_FULFILMENT",
            actor=cls._user(actor),
            obj=order,
            title="Order Inventory Fulfilment",
            message=message,
            level=level,
            metadata={
                "order_id": order.pk,
                "order_number": order.order_number,
                "warehouse_id": warehouse.pk,
                "result_status": result["status"],
                "order_status": order.status,
                "all_reserved": all_reserved,
                "reservation_ids": [
                    reservation.pk
                    for reservation in reservations
                ],
                "shortages": [
                    {
                        **shortage,
                        "requested_quantity": str(
                            shortage["requested_quantity"]
                        ),
                        "reserved_quantity": str(
                            shortage["reserved_quantity"]
                        ),
                        "shortage_quantity": str(
                            shortage["shortage_quantity"]
                        ),
                    }
                    for shortage in shortages
                ],
            },
            notify_groups=[
                "Inventory Manager",
                "Order Manager",
            ],
            notify_owner=True,
        )

        return {
            "order": order,
            "warehouse": warehouse,
            "reservations": reservations,
            "reservation_status": result["status"],
            "all_reserved": all_reserved,
            "order_status": route_status,
            "shortages": shortages,
            "message": message,
        }

    @classmethod
    @transaction.atomic
    def retry_fulfilment(
        cls,
        *,
        order,
        warehouse=None,
        actor=None,
    ):
        valid_retry_statuses = {
            "CONFIRMED",
            "PROCESSING",
            "WAITING_STOCK",
        }

        if order.status not in valid_retry_statuses:
            raise ValidationError(
                "This order is not waiting for inventory fulfilment."
            )

        if order.status == "WAITING_STOCK":
            order.status = "CONFIRMED"
            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return cls.fulfil_order(
            order=order,
            warehouse=warehouse,
            actor=actor,
        )
