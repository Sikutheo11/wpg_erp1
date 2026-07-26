from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine

from inventory.models import (
    StockReservation,
    Warehouse,
)

from .stock_service import StockService


class ReservationService:
    """
    Reserves inventory for order items.

    V1:
    - one reservation per OrderItem
    - reservation is warehouse-specific
    - stock is not deducted until fulfilment or delivery
    """

    @staticmethod
    def _user(actor):
        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(actor, "user", None)

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0))

    @classmethod
    def _validate_order_item(
        cls,
        order_item,
    ):
        if order_item is None:
            raise ValidationError(
                "Order item is required."
            )

        if order_item.product is None:
            raise ValidationError(
                (
                    "A custom item without a catalogue product "
                    "cannot be reserved from inventory."
                )
            )

        if order_item.order.status not in {
            "CONFIRMED",
            "PROCESSING",
            "READY",
        }:
            raise ValidationError(
                (
                    "Stock can only be reserved for confirmed "
                    "or processing orders."
                )
            )

    @classmethod
    @transaction.atomic
    def reserve_item(
        cls,
        *,
        order_item,
        warehouse,
        actor=None,
    ):
        cls._validate_order_item(
            order_item
        )

        if warehouse is None:
            raise ValidationError(
                "Warehouse is required."
            )

        requested_quantity = cls._decimal(
            order_item.quantity
        )

        available_quantity = (
            StockService.available_stock(
                product=order_item.product,
                warehouse=warehouse,
            )
        )

        reserved_quantity = min(
            requested_quantity,
            available_quantity,
        )

        if reserved_quantity >= requested_quantity:
            status = "RESERVED"

        elif reserved_quantity > 0:
            status = "PARTIAL"

        else:
            status = "FAILED"

        reservation, created = (
            StockReservation.objects.update_or_create(
                order_item=order_item,
                defaults={
                    "product": order_item.product,
                    "warehouse": warehouse,
                    "requested_quantity": requested_quantity,
                    "reserved_quantity": reserved_quantity,
                    "status": status,
                    "reserved_by": cls._user(actor),
                    "reserved_at": (
                        timezone.now()
                        if reserved_quantity > 0
                        else None
                    ),
                    "released_at": None,
                    "completed_at": None,
                    "note": "",
                },
            )
        )

        EventEngine.dispatch(
            event_code="INVENTORY_STOCK_RESERVED",
            actor=cls._user(actor),
            obj=reservation,
            title="Stock Reservation Updated",
            message=(
                f"{reserved_quantity} of "
                f"{requested_quantity} "
                f"{order_item.product.name} reserved "
                f"for order "
                f"{order_item.order.order_number}."
            ),
            level=(
                "SUCCESS"
                if status == "RESERVED"
                else "WARNING"
            ),
            metadata={
                "reservation_id": reservation.pk,
                "order_id": order_item.order_id,
                "order_item_id": order_item.pk,
                "product_id": order_item.product_id,
                "warehouse_id": warehouse.pk,
                "requested_quantity": str(
                    requested_quantity
                ),
                "reserved_quantity": str(
                    reserved_quantity
                ),
                "status": status,
                "created": created,
            },
            notify_groups=[
                "Inventory Manager",
                "Order Manager",
            ],
            notify_owner=True,
        )

        return reservation

    @classmethod
    @transaction.atomic
    def reserve_order(
        cls,
        *,
        order,
        warehouse,
        actor=None,
    ):
        if order is None:
            raise ValidationError(
                "Order is required."
            )

        if order.status != "CONFIRMED":
            raise ValidationError(
                "Only confirmed orders can be reserved."
            )

        items = list(
            order.items.select_related(
                "product"
            )
        )

        if not items:
            raise ValidationError(
                "The order has no items."
            )

        reservations = []

        for item in items:
            reservation = cls.reserve_item(
                order_item=item,
                warehouse=warehouse,
                actor=actor,
            )

            reservations.append(
                reservation
            )

        all_reserved = all(
            reservation.status == "RESERVED"
            for reservation in reservations
        )

        any_reserved = any(
            reservation.status in {
                "RESERVED",
                "PARTIAL",
            }
            for reservation in reservations
        )

        if all_reserved:
            result_status = "RESERVED"

        elif any_reserved:
            result_status = "PARTIAL"

        else:
            result_status = "FAILED"

        return {
            "order": order,
            "warehouse": warehouse,
            "reservations": reservations,
            "status": result_status,
            "all_reserved": all_reserved,
        }

    @classmethod
    @transaction.atomic
    def release_reservation(
        cls,
        *,
        reservation,
        actor=None,
        note="",
    ):
        if reservation.status in {
            "RELEASED",
            "COMPLETED",
        }:
            raise ValidationError(
                (
                    "This reservation has already been "
                    "released or completed."
                )
            )

        reservation.status = "RELEASED"
        reservation.reserved_quantity = Decimal(
            "0.00"
        )
        reservation.released_at = timezone.now()
        reservation.note = note or ""

        reservation.save(
            update_fields=[
                "status",
                "reserved_quantity",
                "released_at",
                "note",
                "updated_at",
            ]
        )

        EventEngine.dispatch(
            event_code="INVENTORY_RESERVATION_RELEASED",
            actor=cls._user(actor),
            obj=reservation,
            title="Stock Reservation Released",
            message=(
                f"Stock reservation #{reservation.pk} "
                "was released."
            ),
            level="WARNING",
            metadata={
                "reservation_id": reservation.pk,
                "order_item_id": (
                    reservation.order_item_id
                ),
                "product_id": reservation.product_id,
            },
            notify_groups=[
                "Inventory Manager",
            ],
            notify_owner=True,
        )

        return reservation