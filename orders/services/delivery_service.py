from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine
from inventory.models import StockMovement, StockReservation
from inventory.services import StockService

from .order_service import OrderService


class DeliveryService:
    """
    Completes delivery of READY orders and posts inventory stock-out movements.

    Version 1 responsibilities:
    - validate that the order is ready;
    - verify that every catalogue item is fully reserved;
    - create one OUT StockMovement per completed reservation;
    - mark reservations as COMPLETED;
    - mark the order as DELIVERED;
    - prevent duplicate stock deductions.
    """

    @staticmethod
    def _user(actor):
        """
        Return a User instance whether actor is a User or Employee.
        """

        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(actor, "user", None)

    @staticmethod
    def _employee(actor):
        """
        Return an Employee instance whether actor is a User or Employee.
        """

        if actor is None:
            return None

        if hasattr(actor, "employee_code"):
            return actor

        return getattr(actor, "employee", None)

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0))

    @classmethod
    def _validate_order(cls, order):
        if order is None:
            raise ValidationError(
                "Order is required."
            )

        if order.status == "DELIVERED":
            raise ValidationError(
                "This order has already been delivered."
            )

        if order.status == "COMPLETED":
            raise ValidationError(
                "This order has already been completed."
            )

        if order.status != "READY":
            raise ValidationError(
                "Only ready orders can be delivered."
            )

        if not order.items.exists():
            raise ValidationError(
                "The order has no items."
            )

    @classmethod
    def _get_reservations(cls, order):
        catalogue_items = list(
            order.items
            .select_related("product")
            .filter(product__isnull=False)
        )

        if not catalogue_items:
            raise ValidationError(
                (
                    "This order has no catalogue products "
                    "reserved for inventory delivery."
                )
            )

        reservations = list(
            StockReservation.objects
            .select_related(
                "order_item",
                "product",
                "warehouse",
            )
            .filter(
                order_item__order=order,
            )
            .order_by("id")
        )

        reservation_by_item = {
            reservation.order_item_id: reservation
            for reservation in reservations
        }

        missing_items = [
            item.product_name
            for item in catalogue_items
            if item.pk not in reservation_by_item
        ]

        if missing_items:
            raise ValidationError(
                (
                    "Stock reservations are missing for: "
                    + ", ".join(missing_items)
                )
            )

        incomplete = []

        for item in catalogue_items:
            reservation = reservation_by_item[item.pk]

            if reservation.status != "RESERVED":
                incomplete.append(
                    item.product_name
                )
                continue

            if (
                reservation.reserved_quantity
                < reservation.requested_quantity
            ):
                incomplete.append(
                    item.product_name
                )

        if incomplete:
            raise ValidationError(
                (
                    "The following items are not fully reserved: "
                    + ", ".join(incomplete)
                )
            )

        return [
            reservation_by_item[item.pk]
            for item in catalogue_items
        ]

    @staticmethod
    def _movement_reference(order, reservation):
        return (
            f"DELIVERY-{order.order_number}-"
            f"RES-{reservation.pk}"
        )

    @classmethod
    def _movement_unit_cost(cls, reservation):
        """
        Product currently has no inventory cost field.

        Use an available cost field when present; otherwise store zero.
        Selling price is deliberately not used as inventory cost.
        """

        product = reservation.product

        for field_name in (
            "unit_cost",
            "cost_price",
            "average_cost",
            "purchase_price",
        ):
            value = getattr(
                product,
                field_name,
                None,
            )

            if value is not None:
                return cls._decimal(value)

        return Decimal("0.00")

    @classmethod
    def _create_stock_out(
        cls,
        *,
        order,
        reservation,
        actor=None,
    ):
        reference_no = cls._movement_reference(
            order,
            reservation,
        )

        existing_movement = (
            StockMovement.objects
            .filter(
                movement_type="OUT",
                product=reservation.product,
                warehouse=reservation.warehouse,
                reference_no=reference_no,
            )
            .first()
        )

        if existing_movement:
            return existing_movement, False

        quantity = cls._decimal(
            reservation.reserved_quantity
        )

        if quantity <= 0:
            raise ValidationError(
                (
                    f"Reservation #{reservation.pk} "
                    "has no quantity to deliver."
                )
            )

        actual_stock = StockService.actual_stock(
            product=reservation.product,
            warehouse=reservation.warehouse,
        )

        if actual_stock < quantity:
            raise ValidationError(
                (
                    f"Insufficient physical stock for "
                    f"{reservation.product.name}. "
                    f"Required: {quantity}; "
                    f"available physical stock: {actual_stock}."
                )
            )

        movement = StockMovement.objects.create(
            product=reservation.product,
            raw_material=None,
            movement_type="OUT",
            quantity=quantity,
            unit_cost=cls._movement_unit_cost(
                reservation
            ),
            reference_no=reference_no,
            warehouse=reservation.warehouse,
            created_by=cls._user(actor),
        )

        return movement, True

    @classmethod
    @transaction.atomic
    def deliver_order(
        cls,
        *,
        order,
        delivered_by=None,
        note="",
    ):
        cls._validate_order(order)

        reservations = cls._get_reservations(
            order
        )

        movements = []
        created_movements = []

        for reservation in reservations:
            movement, created = cls._create_stock_out(
                order=order,
                reservation=reservation,
                actor=delivered_by,
            )

            movements.append(movement)

            if created:
                created_movements.append(
                    movement
                )

            reservation.status = "COMPLETED"
            reservation.completed_at = timezone.now()

            if note:
                reservation.note = (
                    f"{reservation.note}\n{note}"
                    if reservation.note
                    else note
                )

            reservation.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "note",
                    "updated_at",
                ]
            )

        OrderService.deliver(
            order=order,
            delivered_by=delivered_by,
        )

        receivable = None

        if order.order_type not in {
            "RESTOCK",
            "NEW_PRODUCT",
        }:
            from finance.services import ReceivableService

            receivable, _ = (
                ReceivableService.create_from_order(
                    order=order,
                    actor=delivered_by,
                )
            )

        EventEngine.dispatch(
            event_code="ORDER_DELIVERY_COMPLETED",
            actor=cls._user(delivered_by),
            obj=order,
            title="Order Delivered",
            message=(
                f"Order {order.order_number} was delivered "
                "and inventory stock was deducted."
            ),
            level="SUCCESS",
            metadata={
                "order_id": order.pk,
                "order_number": order.order_number,
                "movement_ids": [
                    movement.pk
                    for movement in movements
                ],
                "created_movement_ids": [
                    movement.pk
                    for movement in created_movements
                ],
                "reservation_ids": [
                    reservation.pk
                    for reservation in reservations
                ],
                "receivable_id": (
                    receivable.pk
                    if receivable
                    else None
                ),
                "delivered_at": (
                    order.delivered_at.isoformat()
                    if order.delivered_at
                    else None
                ),
            },
            notify_groups=[
                "Inventory Manager",
                "Order Manager",
                "Sales Manager",
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return {
            "order": order,
            "reservations": reservations,
            "movements": movements,
            "created_movements": created_movements,
            "receivable": receivable,
            "message": (
                f"Order {order.order_number} "
                "delivered successfully."
            ),
        }
    @classmethod
    @transaction.atomic
    def mark_shipped(
        cls,
        *,
        order,
        actor=None,
    ):
        """
        Mark a READY order as shipped without deducting stock yet.

        Stock is deducted only when deliver_order() is completed.
        """

        return OrderService.mark_shipped(
            order=order,
            actor=actor,
        )
