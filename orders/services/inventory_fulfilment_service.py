from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from core.event_engine import EventEngine
from inventory.models import StockReservation, Warehouse
from inventory.services.reservation_service import ReservationService
from orders.models import Order


class InventoryFulfilmentService:
    """
    WPG BOS Inventory Fulfilment Service V1.

    Purpose:
    - connect enterprise Orders to Inventory reservations;
    - prepare catalogue items for fulfilment;
    - support partial or complete stock issue;
    - release active reservations when an order is cancelled;
    - provide a shared fulfilment layer for Furniture,
      Construction, Agriculture and Marketplace.

    Important:
    - This service does not create production jobs, projects,
      farm cycles or marketplace shipments.
    - Business-unit routing remains the responsibility of
      OrderRoutingService.
    - Inventory stock changes are delegated to
      ReservationService and StockService.
    """

    RESERVABLE_ORDER_STATUSES = {
        "CONFIRMED",
        "PROCESSING",
        "READY",
    }

    FULFILLABLE_ORDER_STATUSES = {
        "CONFIRMED",
        "PROCESSING",
        "READY",
        "DELIVERED",
    }

    RELEASABLE_ORDER_STATUSES = {
        "PENDING",
        "CONFIRMED",
        "PROCESSING",
        "READY",
        "CANCELLED",
    }

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

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0))

    @classmethod
    def _validate_order(
        cls,
        order,
        *,
        allowed_statuses,
    ):
        if order is None:
            raise ValidationError(
                "Order is required."
            )

        if not isinstance(order, Order):
            raise ValidationError(
                "A valid Order instance is required."
            )

        if not getattr(order, "pk", None):
            raise ValidationError(
                "A saved order is required."
            )

        if order.status not in allowed_statuses:
            raise ValidationError(
                (
                    f"Order {order.order_number} is not in "
                    "a status that allows this fulfilment operation."
                )
            )

        if not order.items.exists():
            raise ValidationError(
                "The order must contain at least one item."
            )

        return order

    @staticmethod
    def _validate_warehouse(warehouse):
        if warehouse is None:
            raise ValidationError(
                "Warehouse is required."
            )

        if not isinstance(warehouse, Warehouse):
            raise ValidationError(
                "A valid Warehouse instance is required."
            )

        if not warehouse.is_active:
            raise ValidationError(
                "Inactive warehouses cannot be used."
            )

        return warehouse

    @classmethod
    def _dispatch_event(
        cls,
        *,
        order,
        actor,
        event_code,
        title,
        message,
        level="INFO",
        metadata=None,
    ):
        event_metadata = {
            "order_id": order.pk,
            "order_number": order.order_number,
            "business_unit": order.business_unit,
            "order_type": order.order_type,
            "order_status": order.status,
        }

        if metadata:
            event_metadata.update(metadata)

        EventEngine.dispatch(
            event_code=event_code,
            actor=cls._user(actor),
            obj=order,
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
    # FULFILMENT SUMMARY
    # =====================================================

    @classmethod
    def fulfilment_summary(
        cls,
        *,
        order,
    ):
        cls._validate_order(
            order,
            allowed_statuses={
                "PENDING",
                "CONFIRMED",
                "PROCESSING",
                "READY",
                "DELIVERED",
                "COMPLETED",
                "CANCELLED",
            },
        )

        items = list(
            order.items.select_related(
                "product"
            ).order_by("pk")
        )

        reservations = {
            reservation.order_item_id: reservation
            for reservation in (
                StockReservation.objects
                .select_related(
                    "product",
                    "warehouse",
                    "order_item",
                )
                .filter(
                    order_item__order=order
                )
            )
        }

        lines = []

        total_catalogue_items = 0
        total_custom_items = 0
        fully_reserved_items = 0
        partially_reserved_items = 0
        completed_items = 0
        failed_items = 0

        for item in items:
            reservation = reservations.get(
                item.pk
            )

            tracks_inventory = bool(
                item.product
                and item.product.track_inventory
            )

            if tracks_inventory:
                total_catalogue_items += 1
            else:
                total_custom_items += 1

            if reservation:
                if reservation.status == "RESERVED":
                    fully_reserved_items += 1
                elif reservation.status == "PARTIAL":
                    partially_reserved_items += 1
                elif reservation.status == "COMPLETED":
                    completed_items += 1
                elif reservation.status == "FAILED":
                    failed_items += 1

            lines.append(
                {
                    "order_item": item,
                    "product": item.product,
                    "tracks_inventory": tracks_inventory,
                    "reservation": reservation,
                    "requested_quantity": cls._decimal(
                        item.quantity
                    ),
                    "reserved_quantity": (
                        cls._decimal(
                            reservation.reserved_quantity
                        )
                        if reservation
                        else Decimal("0.00")
                    ),
                    "completed_quantity": (
                        cls._decimal(
                            reservation.completed_quantity
                        )
                        if reservation
                        else Decimal("0.00")
                    ),
                    "remaining_reserved_quantity": (
                        reservation.remaining_reserved_quantity
                        if reservation
                        else Decimal("0.00")
                    ),
                    "status": (
                        reservation.status
                        if reservation
                        else (
                            "NOT_REQUIRED"
                            if not tracks_inventory
                            else "NOT_RESERVED"
                        )
                    ),
                }
            )

        inventory_required = (
            total_catalogue_items > 0
        )

        all_inventory_completed = (
            inventory_required
            and completed_items
            == total_catalogue_items
        )

        all_inventory_reserved = (
            inventory_required
            and (
                fully_reserved_items
                + completed_items
            )
            == total_catalogue_items
        )

        return {
            "order": order,
            "lines": lines,
            "inventory_required": inventory_required,
            "total_items": len(items),
            "total_catalogue_items": total_catalogue_items,
            "total_custom_items": total_custom_items,
            "fully_reserved_items": fully_reserved_items,
            "partially_reserved_items": partially_reserved_items,
            "completed_items": completed_items,
            "failed_items": failed_items,
            "all_inventory_reserved": all_inventory_reserved,
            "all_inventory_completed": all_inventory_completed,
        }

    # =====================================================
    # PREPARE ORDER FOR FULFILMENT
    # =====================================================

    @classmethod
    @transaction.atomic
    def prepare_order(
        cls,
        *,
        order,
        warehouse,
        actor=None,
        note="",
        strict=False,
    ):
        """
        Reserve all inventory-tracked items in an order.

        Custom products and services are skipped because they
        have no catalogue stock.
        """

        cls._validate_order(
            order,
            allowed_statuses=cls.RESERVABLE_ORDER_STATUSES,
        )
        cls._validate_warehouse(
            warehouse
        )

        result = ReservationService.reserve_order(
            order=order,
            warehouse=warehouse,
            actor=actor,
            note=note,
            strict=strict,
        )

        cls._dispatch_event(
            order=order,
            actor=actor,
            event_code="ORDER_INVENTORY_PREPARED",
            title="Order Inventory Prepared",
            message=(
                f"Inventory preparation for order "
                f"{order.order_number} finished with "
                f"status {result['status']}."
            ),
            level=(
                "SUCCESS"
                if result["status"]
                in {
                    "RESERVED",
                    "NOT_REQUIRED",
                }
                else "WARNING"
            ),
            metadata={
                "warehouse_id": warehouse.pk,
                "warehouse_name": warehouse.name,
                "reservation_status": result["status"],
                "reservation_ids": [
                    reservation.pk
                    for reservation
                    in result["reservations"]
                ],
                "reservation_count": len(
                    result["reservations"]
                ),
                "skipped_item_ids": [
                    item.pk
                    for item in result["skipped_items"]
                ],
                "failed_item_ids": [
                    failure["item"].pk
                    for failure in result["failed_items"]
                ],
            },
        )

        return result

    # =====================================================
    # FULFIL ONE RESERVATION
    # =====================================================

    @classmethod
    @transaction.atomic
    def fulfil_reservation(
        cls,
        *,
        reservation,
        quantity=None,
        actor=None,
        note="",
    ):
        """
        Issue all or part of one active reservation.
        """

        if reservation is None or not getattr(
            reservation,
            "pk",
            None,
        ):
            raise ValidationError(
                "A saved reservation is required."
            )

        order = reservation.order_item.order

        cls._validate_order(
            order,
            allowed_statuses=cls.FULFILLABLE_ORDER_STATUSES,
        )

        result = ReservationService.complete_reservation(
            reservation=reservation,
            quantity=quantity,
            actor=actor,
            note=note,
        )

        cls._dispatch_event(
            order=order,
            actor=actor,
            event_code="ORDER_ITEM_INVENTORY_FULFILLED",
            title="Order Item Inventory Fulfilled",
            message=(
                f"{result['completed_quantity']} "
                f"{result['reservation'].product.unit} of "
                f"{result['reservation'].product.name} "
                f"issued for order "
                f"{order.order_number}."
            ),
            level="SUCCESS",
            metadata={
                "reservation_id": (
                    result["reservation"].pk
                ),
                "order_item_id": (
                    result["reservation"].order_item_id
                ),
                "stock_movement_id": (
                    result["movement"].pk
                ),
                "completed_quantity": str(
                    result["completed_quantity"]
                ),
                "reservation_status": result["status"],
            },
        )

        return result

    # =====================================================
    # FULFIL COMPLETE ORDER
    # =====================================================

    @classmethod
    @transaction.atomic
    def fulfil_order(
        cls,
        *,
        order,
        actor=None,
        note="",
        strict=True,
    ):
        """
        Complete all active inventory reservations for an order.

        When strict=True, one failed line rolls back the complete
        order fulfilment transaction.
        """

        cls._validate_order(
            order,
            allowed_statuses=cls.FULFILLABLE_ORDER_STATUSES,
        )

        result = (
            ReservationService
            .complete_order_reservations(
                order=order,
                actor=actor,
                note=note,
                strict=strict,
            )
        )

        summary = cls.fulfilment_summary(
            order=order
        )

        cls._dispatch_event(
            order=order,
            actor=actor,
            event_code="ORDER_INVENTORY_FULFILLED",
            title="Order Inventory Fulfilled",
            message=(
                f"Inventory fulfilment for order "
                f"{order.order_number} completed. "
                f"{len(result['completed'])} reservation(s) "
                "were processed."
            ),
            level=(
                "SUCCESS"
                if result["all_completed"]
                else "WARNING"
            ),
            metadata={
                "completed_reservation_ids": [
                    entry["reservation"].pk
                    for entry in result["completed"]
                ],
                "stock_movement_ids": [
                    entry["movement"].pk
                    for entry in result["completed"]
                ],
                "failed_reservation_ids": [
                    entry["reservation"].pk
                    for entry in result["failed"]
                ],
                "all_completed": result["all_completed"],
                "all_inventory_completed": (
                    summary[
                        "all_inventory_completed"
                    ]
                ),
            },
        )

        return {
            **result,
            "summary": summary,
        }

    # =====================================================
    # RELEASE ORDER INVENTORY
    # =====================================================

    @classmethod
    @transaction.atomic
    def release_order(
        cls,
        *,
        order,
        actor=None,
        note="",
    ):
        """
        Release reservations that have not yet been issued.

        This operation does not reverse stock already issued.
        Posted stock movements must be reversed separately.
        """

        cls._validate_order(
            order,
            allowed_statuses=cls.RELEASABLE_ORDER_STATUSES,
        )

        result = (
            ReservationService
            .release_order_reservations(
                order=order,
                actor=actor,
                note=note,
            )
        )

        cls._dispatch_event(
            order=order,
            actor=actor,
            event_code="ORDER_INVENTORY_RELEASED",
            title="Order Inventory Released",
            message=(
                f"{result['released_count']} stock "
                f"reservation(s) were released for "
                f"order {order.order_number}."
            ),
            level="WARNING",
            metadata={
                "released_reservation_ids": [
                    reservation.pk
                    for reservation
                    in result["released"]
                ],
                "released_count": (
                    result["released_count"]
                ),
                "reason": cls._clean_text(note),
            },
        )

        return result

    # =====================================================
    # AUTOMATIC INVENTORY FLOW
    # =====================================================

    @classmethod
    @transaction.atomic
    def prepare_and_fulfil_order(
        cls,
        *,
        order,
        warehouse,
        actor=None,
        note="",
        strict=True,
    ):
        """
        Reserve and immediately issue catalogue stock.

        Use this for direct stock fulfilment such as:
        - Marketplace ready-made products
        - Ecommerce orders
        - POS orders
        - Furniture products already available in stock

        Do not use this for production orders that still require
        manufacturing.
        """

        preparation = cls.prepare_order(
            order=order,
            warehouse=warehouse,
            actor=actor,
            note=note,
            strict=strict,
        )

        if preparation["status"] == "FAILED":
            raise ValidationError(
                (
                    "Order inventory could not be reserved "
                    "and therefore cannot be fulfilled."
                )
            )

        if (
            strict
            and preparation["status"] == "PARTIAL"
        ):
            raise ValidationError(
                (
                    "Strict fulfilment requires complete "
                    "stock reservation."
                )
            )

        active_reservations = (
            StockReservation.objects.filter(
                order_item__order=order,
                status__in={
                    "RESERVED",
                    "PARTIAL",
                },
            ).exists()
        )

        if not active_reservations:
            summary = cls.fulfilment_summary(
                order=order
            )

            return {
                "preparation": preparation,
                "fulfilment": None,
                "summary": summary,
                "message": (
                    "The order has no inventory-tracked "
                    "items requiring stock issue."
                ),
            }

        fulfilment = cls.fulfil_order(
            order=order,
            actor=actor,
            note=note,
            strict=strict,
        )

        return {
            "preparation": preparation,
            "fulfilment": fulfilment,
            "summary": fulfilment["summary"],
            "message": (
                f"Order {order.order_number} inventory "
                "was prepared and fulfilled."
            ),
        }
