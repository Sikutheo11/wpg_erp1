from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine

from inventory.models import (
    Product,
    StockReservation,
    Warehouse,
)

from .stock_service import StockService


class ReservationService:
    """
    WPG BOS Reservation Service V2.

    Responsibilities:
    - reserve stock for catalogue OrderItems;
    - support complete, partial and failed reservations;
    - prevent over-reservation through database row locks;
    - release remaining reservations without destroying audit values;
    - complete reservations by posting StockMovement OUT records;
    - support partial fulfilment;
    - dispatch inventory events and notifications.

    Inventory remains the single source of truth for:
    - Furniture
    - Construction
    - Agriculture / Poultry
    - Marketplace / Ecommerce
    """

    ACTIVE_STATUSES = {
        "RESERVED",
        "PARTIAL",
    }

    RESERVABLE_ORDER_STATUSES = {
        "CONFIRMED",
        "PROCESSING",
        "READY",
    }

    COMPLETABLE_ORDER_STATUSES = {
        "CONFIRMED",
        "PROCESSING",
        "READY",
        "DELIVERED",
    }

    QUANTITY_QUANTIZER = Decimal("0.01")

    # =====================================================
    # BASIC HELPERS
    # =====================================================

    @staticmethod
    def _user(actor):
        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(actor, "user", None)

    @classmethod
    def _decimal(cls, value):
        return Decimal(str(value or 0))

    @classmethod
    def _quantity(cls, value):
        return cls._decimal(value).quantize(
            cls.QUANTITY_QUANTIZER
        )

    @staticmethod
    def _clean_text(value):
        return (value or "").strip()

    @classmethod
    def _validate_order_item(
        cls,
        order_item,
        *,
        for_completion=False,
    ):
        if order_item is None:
            raise ValidationError(
                "Order item is required."
            )

        if not getattr(order_item, "pk", None):
            raise ValidationError(
                "A saved order item is required."
            )

        if order_item.product is None:
            raise ValidationError(
                (
                    "A custom item without a catalogue product "
                    "does not require an inventory reservation."
                )
            )

        if not order_item.product.track_inventory:
            raise ValidationError(
                (
                    f"{order_item.product.name} does not track "
                    "inventory and cannot be reserved."
                )
            )

        allowed_statuses = (
            cls.COMPLETABLE_ORDER_STATUSES
            if for_completion
            else cls.RESERVABLE_ORDER_STATUSES
        )

        if order_item.order.status not in allowed_statuses:
            raise ValidationError(
                (
                    "The order is not in a status that allows "
                    "this stock reservation operation."
                )
            )

    @staticmethod
    def _validate_warehouse(warehouse):
        if warehouse is None:
            raise ValidationError(
                "Warehouse is required."
            )

        if not isinstance(warehouse, Warehouse):
            raise ValidationError(
                "A valid Warehouse is required."
            )

        if not warehouse.is_active:
            raise ValidationError(
                "Inactive warehouses cannot be used."
            )

    @classmethod
    def _lock_product_and_warehouse(
        cls,
        *,
        product,
        warehouse,
    ):
        """
        Serialize reservation operations for the same
        product and warehouse combination.
        """

        locked_product = (
            Product._base_manager
            .select_related(None)
            .select_for_update(of=("self",))
            .get(pk=product.pk)
        )

        locked_warehouse = (
            Warehouse._base_manager
            .select_related(None)
            .select_for_update(of=("self",))
            .get(pk=warehouse.pk)
        )

        return locked_product, locked_warehouse

    @classmethod
    def _other_reserved_stock(
        cls,
        *,
        product,
        warehouse,
        exclude_reservation_id=None,
    ):
        queryset = StockReservation.objects.filter(
            product=product,
            warehouse=warehouse,
            status__in=cls.ACTIVE_STATUSES,
        )

        if exclude_reservation_id:
            queryset = queryset.exclude(
                pk=exclude_reservation_id
            )

        total = Decimal("0.00")

        for values in queryset.values(
            "reserved_quantity",
            "completed_quantity",
        ):
            remaining = (
                cls._decimal(
                    values["reserved_quantity"]
                )
                - cls._decimal(
                    values["completed_quantity"]
                )
            )

            if remaining > 0:
                total += remaining

        return total

    @classmethod
    def _dispatch_event(
        cls,
        *,
        reservation,
        actor,
        event_code,
        title,
        message,
        level="INFO",
        metadata=None,
    ):
        event_metadata = {
            "reservation_id": reservation.pk,
            "order_id": reservation.order_item.order_id,
            "order_item_id": reservation.order_item_id,
            "product_id": reservation.product_id,
            "product_name": reservation.product.name,
            "warehouse_id": reservation.warehouse_id,
            "warehouse_name": reservation.warehouse.name,
            "requested_quantity": str(
                reservation.requested_quantity
            ),
            "reserved_quantity": str(
                reservation.reserved_quantity
            ),
            "completed_quantity": str(
                reservation.completed_quantity
            ),
            "remaining_reserved_quantity": str(
                reservation.remaining_reserved_quantity
            ),
            "status": reservation.status,
        }

        if metadata:
            event_metadata.update(metadata)

        EventEngine.dispatch(
            event_code=event_code,
            actor=cls._user(actor),
            obj=reservation,
            title=title,
            message=message,
            level=level,
            metadata=event_metadata,
            notify_groups=[
                "Inventory Manager",
                "Order Manager",
            ],
            notify_owner=True,
        )

    # =====================================================
    # RESERVE ONE ORDER ITEM
    # =====================================================

    @classmethod
    @transaction.atomic
    def reserve_item(
        cls,
        *,
        order_item,
        warehouse,
        actor=None,
        note="",
    ):
        cls._validate_order_item(
            order_item
        )
        cls._validate_warehouse(
            warehouse
        )

        product, warehouse = (
            cls._lock_product_and_warehouse(
                product=order_item.product,
                warehouse=warehouse,
            )
        )

        reservation = (
            StockReservation.objects
            .select_for_update()
            .filter(
                order_item=order_item
            )
            .first()
        )

        requested_quantity = cls._quantity(
            order_item.quantity
        )

        if requested_quantity <= 0:
            raise ValidationError(
                "Requested quantity must be greater than zero."
            )

        completed_quantity = (
            cls._quantity(
                reservation.completed_quantity
            )
            if reservation
            else Decimal("0.00")
        )

        if completed_quantity > requested_quantity:
            raise ValidationError(
                (
                    "Completed reservation quantity exceeds "
                    "the current order item quantity."
                )
            )

        remaining_requested = max(
            requested_quantity - completed_quantity,
            Decimal("0.00"),
        )

        actual_stock = StockService.actual_stock(
            product=product,
            warehouse=warehouse,
        )

        other_reserved = cls._other_reserved_stock(
            product=product,
            warehouse=warehouse,
            exclude_reservation_id=(
                reservation.pk
                if reservation
                else None
            ),
        )

        available_for_this_reservation = max(
            actual_stock - other_reserved,
            Decimal("0.00"),
        )

        newly_reservable = min(
            remaining_requested,
            available_for_this_reservation,
        )

        target_reserved_quantity = (
            completed_quantity
            + newly_reservable
        )

        if completed_quantity >= requested_quantity:
            status = "COMPLETED"

        elif target_reserved_quantity >= requested_quantity:
            status = "RESERVED"

        elif target_reserved_quantity > completed_quantity:
            status = "PARTIAL"

        else:
            status = "FAILED"

        now = timezone.now()

        defaults = {
            "product": product,
            "warehouse": warehouse,
            "requested_quantity": requested_quantity,
            "reserved_quantity": (
                target_reserved_quantity
            ),
            "completed_quantity": completed_quantity,
            "status": status,
            "reserved_by": cls._user(actor),
            "reserved_at": (
                now
                if newly_reservable > 0
                else (
                    reservation.reserved_at
                    if reservation
                    else None
                )
            ),
            "released_at": None,
            "completed_at": (
                now
                if status == "COMPLETED"
                else None
            ),
            "note": cls._clean_text(note),
        }

        if reservation is None:
            reservation = StockReservation.objects.create(
                order_item=order_item,
                **defaults,
            )
            created = True
        else:
            for field_name, value in defaults.items():
                setattr(
                    reservation,
                    field_name,
                    value,
                )

            reservation.full_clean()
            reservation.save()
            created = False

        level = (
            "SUCCESS"
            if status in {
                "RESERVED",
                "COMPLETED",
            }
            else "WARNING"
        )

        cls._dispatch_event(
            reservation=reservation,
            actor=actor,
            event_code="INVENTORY_STOCK_RESERVED",
            title="Stock Reservation Updated",
            message=(
                f"{reservation.reserved_quantity} of "
                f"{reservation.requested_quantity} "
                f"{reservation.product.name} reserved for "
                f"order "
                f"{reservation.order_item.order.order_number}."
            ),
            level=level,
            metadata={
                "created": created,
                "actual_stock": str(
                    actual_stock
                ),
                "other_reserved_stock": str(
                    other_reserved
                ),
                "newly_reservable_quantity": str(
                    newly_reservable
                ),
            },
        )

        return reservation

    # =====================================================
    # RESERVE A COMPLETE ORDER
    # =====================================================

    @classmethod
    @transaction.atomic
    def reserve_order(
        cls,
        *,
        order,
        warehouse,
        actor=None,
        note="",
        strict=False,
    ):
        if order is None:
            raise ValidationError(
                "Order is required."
            )

        if not getattr(order, "pk", None):
            raise ValidationError(
                "A saved order is required."
            )

        if order.status not in cls.RESERVABLE_ORDER_STATUSES:
            raise ValidationError(
                (
                    "Only confirmed, processing or ready "
                    "orders can be reserved."
                )
            )

        cls._validate_warehouse(
            warehouse
        )

        items = list(
            order.items.select_related(
                "product"
            ).order_by("pk")
        )

        if not items:
            raise ValidationError(
                "The order has no items."
            )

        reservations = []
        skipped_items = []
        failed_items = []

        for item in items:
            if (
                item.product is None
                or not item.product.track_inventory
            ):
                skipped_items.append(item)
                continue

            try:
                reservation = cls.reserve_item(
                    order_item=item,
                    warehouse=warehouse,
                    actor=actor,
                    note=note,
                )
            except ValidationError as error:
                if strict:
                    raise

                failed_items.append(
                    {
                        "item": item,
                        "error": error,
                    }
                )
                continue

            reservations.append(
                reservation
            )

        required_reservations = len(
            reservations
        ) + len(
            failed_items
        )

        if required_reservations == 0:
            result_status = "NOT_REQUIRED"
            all_reserved = True
            any_reserved = False

        else:
            all_reserved = (
                not failed_items
                and all(
                    reservation.status
                    in {
                        "RESERVED",
                        "COMPLETED",
                    }
                    for reservation in reservations
                )
            )

            any_reserved = any(
                reservation.status
                in {
                    "RESERVED",
                    "PARTIAL",
                    "COMPLETED",
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
            "skipped_items": skipped_items,
            "failed_items": failed_items,
            "status": result_status,
            "all_reserved": all_reserved,
            "any_reserved": any_reserved,
        }

    # =====================================================
    # COMPLETE / FULFIL A RESERVATION
    # =====================================================

    @classmethod
    @transaction.atomic
    def complete_reservation(
        cls,
        *,
        reservation,
        quantity=None,
        actor=None,
        note="",
    ):
        if reservation is None or not getattr(
            reservation,
            "pk",
            None,
        ):
            raise ValidationError(
                "A saved reservation is required."
            )

        reservation = (
            StockReservation.objects
            .select_for_update()
            .get(pk=reservation.pk)
        )

        order_item = reservation.order_item

        cls._validate_order_item(
            order_item,
            for_completion=True,
        )

        if reservation.status not in {
            "RESERVED",
            "PARTIAL",
        }:
            raise ValidationError(
                (
                    "Only reserved or partially reserved "
                    "stock can be completed."
                )
            )

        product, warehouse = (
            cls._lock_product_and_warehouse(
                product=reservation.product,
                warehouse=reservation.warehouse,
            )
        )

        remaining_reserved = (
            reservation.remaining_reserved_quantity
        )

        if remaining_reserved <= 0:
            raise ValidationError(
                (
                    "This reservation has no remaining "
                    "quantity to complete."
                )
            )

        completion_quantity = (
            remaining_reserved
            if quantity is None
            else cls._quantity(quantity)
        )

        if completion_quantity <= 0:
            raise ValidationError(
                "Completion quantity must be greater than zero."
            )

        if completion_quantity > remaining_reserved:
            raise ValidationError(
                (
                    "Completion quantity cannot exceed "
                    "the remaining reserved quantity."
                )
            )

        order = order_item.order

        reference_type = (
            "ECOMMERCE_ORDER"
            if order.business_unit == "MARKETPLACE"
            else "SALES_ORDER"
        )

        movement = StockService.issue_stock(
            product=product,
            warehouse=warehouse,
            quantity=completion_quantity,
            unit_cost=product.standard_cost,
            business_unit=(
                order.business_unit
                or product.business_unit
            ),
            reference_type=reference_type,
            reference_id=str(order.pk),
            reference_no=order.order_number,
            notes=(
                cls._clean_text(note)
                or (
                    "Stock issued from reservation "
                    f"#{reservation.pk}."
                )
            ),
            actor=actor,
            include_reserved_stock=True,
        )

        reservation.completed_quantity = (
            cls._quantity(
                reservation.completed_quantity
            )
            + completion_quantity
        )

        if (
            reservation.completed_quantity
            >= reservation.requested_quantity
        ):
            reservation.status = "COMPLETED"
            reservation.completed_at = timezone.now()

        else:
            reservation.status = "PARTIAL"
            reservation.completed_at = None

        if note:
            reservation.note = cls._clean_text(
                note
            )

        reservation.full_clean()
        reservation.save(
            update_fields=[
                "completed_quantity",
                "status",
                "completed_at",
                "note",
                "updated_at",
            ]
        )

        cls._dispatch_event(
            reservation=reservation,
            actor=actor,
            event_code="INVENTORY_RESERVATION_COMPLETED",
            title="Stock Reservation Fulfilled",
            message=(
                f"{completion_quantity} "
                f"{reservation.product.unit} of "
                f"{reservation.product.name} issued for "
                f"order {order.order_number}."
            ),
            level="SUCCESS",
            metadata={
                "stock_movement_id": movement.pk,
                "completion_quantity": str(
                    completion_quantity
                ),
            },
        )

        return {
            "reservation": reservation,
            "movement": movement,
            "completed_quantity": (
                completion_quantity
            ),
            "status": reservation.status,
        }

    @classmethod
    @transaction.atomic
    def complete_order_reservations(
        cls,
        *,
        order,
        actor=None,
        note="",
        strict=True,
    ):
        if order is None or not getattr(
            order,
            "pk",
            None,
        ):
            raise ValidationError(
                "A saved order is required."
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
                status__in={
                    "RESERVED",
                    "PARTIAL",
                },
            )
            .order_by("pk")
        )

        if not reservations:
            raise ValidationError(
                (
                    "This order has no active stock "
                    "reservations to complete."
                )
            )

        completed = []
        failed = []

        for reservation in reservations:
            try:
                result = cls.complete_reservation(
                    reservation=reservation,
                    actor=actor,
                    note=note,
                )
            except ValidationError as error:
                if strict:
                    raise

                failed.append(
                    {
                        "reservation": reservation,
                        "error": error,
                    }
                )
                continue

            completed.append(result)

        return {
            "order": order,
            "completed": completed,
            "failed": failed,
            "all_completed": (
                bool(completed)
                and not failed
            ),
        }

    # =====================================================
    # RELEASE / CANCEL RESERVATION
    # =====================================================

    @classmethod
    @transaction.atomic
    def release_reservation(
        cls,
        *,
        reservation,
        actor=None,
        note="",
    ):
        if reservation is None or not getattr(
            reservation,
            "pk",
            None,
        ):
            raise ValidationError(
                "A saved reservation is required."
            )

        reservation = (
            StockReservation.objects
            .select_for_update()
            .get(pk=reservation.pk)
        )

        if reservation.status in {
            "RELEASED",
            "COMPLETED",
            "CANCELLED",
        }:
            raise ValidationError(
                (
                    "This reservation has already been "
                    "released, completed or cancelled."
                )
            )

        released_quantity = (
            reservation.remaining_reserved_quantity
        )

        reservation.status = "RELEASED"
        reservation.released_at = timezone.now()
        reservation.note = cls._clean_text(note)

        # Keep requested, reserved and completed quantities
        # unchanged for a complete audit trail. RELEASED is not
        # counted by StockService.reserved_stock().
        reservation.save(
            update_fields=[
                "status",
                "released_at",
                "note",
                "updated_at",
            ]
        )

        cls._dispatch_event(
            reservation=reservation,
            actor=actor,
            event_code="INVENTORY_RESERVATION_RELEASED",
            title="Stock Reservation Released",
            message=(
                f"{released_quantity} "
                f"{reservation.product.unit} of "
                f"{reservation.product.name} released from "
                f"reservation #{reservation.pk}."
            ),
            level="WARNING",
            metadata={
                "released_quantity": str(
                    released_quantity
                ),
            },
        )

        return reservation

    @classmethod
    @transaction.atomic
    def release_order_reservations(
        cls,
        *,
        order,
        actor=None,
        note="",
    ):
        if order is None or not getattr(
            order,
            "pk",
            None,
        ):
            raise ValidationError(
                "A saved order is required."
            )

        reservations = list(
            StockReservation.objects.filter(
                order_item__order=order,
                status__in={
                    "PENDING",
                    "RESERVED",
                    "PARTIAL",
                    "FAILED",
                },
            ).order_by("pk")
        )

        released = []

        for reservation in reservations:
            released.append(
                cls.release_reservation(
                    reservation=reservation,
                    actor=actor,
                    note=note,
                )
            )

        return {
            "order": order,
            "released": released,
            "released_count": len(released),
        }
