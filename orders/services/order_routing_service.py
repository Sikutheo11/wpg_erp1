from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from core.event_engine import EventEngine
from inventory.models import Warehouse
from inventory.services.stock_service import StockService

from ..models import Order
from .inventory_fulfilment_service import (
    InventoryFulfilmentService,
)


class OrderRoutingService:
    """
    Routes confirmed enterprise orders to the responsible
    business-unit workflow.

    Active routing:
    - Furniture production orders create Production Jobs.
    - Furniture Ecommerce/POS orders reserve available inventory.
    - Agriculture Ecommerce/POS orders reserve available inventory.
    - Construction and Marketplace remain pending integrations.
    """

    FURNITURE_PRODUCTION_TYPES = {
        "CUSTOM_FURNITURE",
        "RESTOCK",
        "NEW_PRODUCT",
    }

    FURNITURE_JOB_TYPE_MAP = {
        "CUSTOM_FURNITURE": "CUSTOMER_CUSTOM",
        "RESTOCK": "RESTOCK",
        "NEW_PRODUCT": "NEW_PRODUCT",
    }

    @staticmethod
    def _user(actor):
        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(actor, "user", None)

    @staticmethod
    def _employee(actor):
        if actor is None:
            return None

        if hasattr(actor, "employee_code"):
            return actor

        return getattr(actor, "employee", None)

    @classmethod
    def _validate_order(cls, order):
        if order is None:
            raise ValidationError(
                "Order is required."
            )

        if order.status != "CONFIRMED":
            raise ValidationError(
                "Only confirmed orders can be routed."
            )

        if not order.items.exists():
            raise ValidationError(
                "The order must have at least one item."
            )

    @classmethod
    @transaction.atomic
    def route_confirmed_order(
        cls,
        *,
        order,
        actor=None,
    ):
        cls._validate_order(order)

        if order.business_unit == "FURNITURE":
            result = cls._route_furniture(
                order=order,
                actor=actor,
            )

        elif order.business_unit == "CONSTRUCTION":
            result = {
                "business_unit": "CONSTRUCTION",
                "route": "CONSTRUCTION_PENDING",
                "object": None,
                "created": False,
                "message": (
                    "Construction routing is not yet connected."
                ),
            }

        elif order.business_unit == "AGRICULTURE":
            result = cls._route_agriculture(
                order=order,
                actor=actor,
            )

        elif order.business_unit == "MARKETPLACE":
            result = {
                "business_unit": "MARKETPLACE",
                "route": "MARKETPLACE_PENDING",
                "object": None,
                "created": False,
                "message": (
                    "Marketplace routing is not yet connected."
                ),
            }

        else:
            raise ValidationError(
                "Unsupported order business unit."
            )

        EventEngine.dispatch(
            event_code="ORDER_ROUTED",
            actor=cls._user(actor),
            obj=order,
            title="Order Routed",
            message=result["message"],
            level="INFO",
            metadata={
                "order_id": order.pk,
                "order_number": order.order_number,
                "business_unit": order.business_unit,
                "order_type": order.order_type,
                "route": result["route"],
                "created": result["created"],
            },
            notify_groups=[
                "Order Manager",
            ],
            notify_owner=True,
        )

        return result

    @classmethod
    def _route_agriculture(
        cls,
        *,
        order,
        actor=None,
    ):
        if order.order_type in {
            "ECOMMERCE",
            "POS",
        }:
            return cls._route_available_inventory(
                order=order,
                actor=actor,
                business_unit="AGRICULTURE",
                route_code="AGRICULTURE_FULFILMENT",
            )

        return {
            "business_unit": "AGRICULTURE",
            "route": "AGRICULTURE_OPERATION",
            "object": None,
            "created": False,
            "message": (
                f"Agriculture order {order.order_number} requires "
                "an Agriculture Operation workflow."
            ),
        }

    @classmethod
    def _route_available_inventory(
        cls,
        *,
        order,
        actor=None,
        business_unit,
        route_code,
    ):
        requirements = {}

        for item in order.items.select_related("product").order_by("pk"):
            if item.product_id is None:
                return {
                    "business_unit": business_unit,
                    "route": f"{business_unit}_PRODUCT_REQUIRED",
                    "object": None,
                    "created": False,
                    "message": (
                        f"Order item {item.product_name} has no "
                        "Inventory Product assigned."
                    ),
                }

            if item.product.business_unit != business_unit:
                raise ValidationError(
                    (
                        f"Product {item.product.name} belongs to "
                        f"{item.product.business_unit}, not {business_unit}."
                    )
                )

            requirement = requirements.setdefault(
                item.product_id,
                {
                    "product": item.product,
                    "quantity": Decimal("0.00"),
                },
            )
            requirement["quantity"] += Decimal(str(item.quantity))

        warehouses = list(
            Warehouse.objects
            .filter(
                business_unit=business_unit,
                is_active=True,
            )
            .order_by("name", "pk")
        )

        if not warehouses:
            return {
                "business_unit": business_unit,
                "route": f"{business_unit}_WAREHOUSE_REQUIRED",
                "object": None,
                "created": False,
                "message": (
                    f"No active {business_unit.title()} warehouse "
                    "was found."
                ),
            }

        selected_warehouse = None
        shortage_details = []

        for warehouse in warehouses:
            warehouse_shortages = []

            for requirement in requirements.values():
                product = requirement["product"]
                required_quantity = requirement["quantity"]

                available_quantity = StockService.available_stock(
                    product=product,
                    warehouse=warehouse,
                )

                if available_quantity < required_quantity:
                    warehouse_shortages.append(
                        (
                            f"{product.name}: required "
                            f"{required_quantity}, available "
                            f"{available_quantity}"
                        )
                    )

            if not warehouse_shortages:
                selected_warehouse = warehouse
                break

            shortage_details.append(
                f"{warehouse.name} — "
                + "; ".join(warehouse_shortages)
            )

        if selected_warehouse is None:
            return {
                "business_unit": business_unit,
                "route": f"{business_unit}_STOCK_SHORTAGE",
                "object": None,
                "created": False,
                "message": (
                    f"No {business_unit.title()} warehouse can completely "
                    f"fulfil order {order.order_number}. "
                    + " | ".join(shortage_details)
                ),
            }

        return cls._route_inventory_fulfilment(
            order=order,
            actor=actor,
            warehouse_code=selected_warehouse.code,
            route_code=route_code,
        )

    @classmethod
    def _route_furniture(
        cls,
        *,
        order,
        actor=None,
    ):
        if order.order_type in cls.FURNITURE_PRODUCTION_TYPES:
            production_job, created = (
                cls._create_furniture_production_job(
                    order=order,
                    actor=actor,
                )
            )

            return {
                "business_unit": "FURNITURE",
                "route": "FURNITURE_PRODUCTION",
                "object": production_job,
                "created": created,
                "message": (
                    f"Order {order.order_number} was routed "
                    f"to Production Job #{production_job.pk}."
                ),
            }

        if order.order_type in {
            "ECOMMERCE",
            "POS",
        }:
            return cls._route_available_inventory(
                order=order,
                actor=actor,
                business_unit="FURNITURE",
                route_code="FURNITURE_FULFILMENT",
            )

        raise ValidationError(
            (
                "This furniture order type does not have "
                "a configured routing rule."
            )
        )

    @classmethod
    def _create_furniture_production_job(
        cls,
        *,
        order,
        actor=None,
    ):
        # Local imports help avoid circular imports.
        from furniture.models import ProductionJob
        from furniture.services import ProductionService

        existing_job = (
            ProductionJob.objects
            .filter(order=order)
            .first()
        )

        if existing_job:
            return existing_job, False

        items = list(
            order.items.select_related(
                "product"
            )
        )

        quantity_to_produce = sum(
            item.quantity
            for item in items
        )

        # ProductionJob currently supports one optional product.
        # Use it only when the order has exactly one catalog product.
        product = None

        if (
            len(items) == 1
            and items[0].product_id
        ):
            product = items[0].product

        job_type = cls.FURNITURE_JOB_TYPE_MAP.get(
            order.order_type
        )

        if not job_type:
            raise ValidationError(
                "Furniture production job type is not configured."
            )

        description_lines = [
            (
                f"Automatically created from "
                f"Order {order.order_number}."
            ),
        ]

        for item in items:
            description_lines.append(
                (
                    f"- {item.product_name}: "
                    f"{item.quantity}"
                )
            )

            if item.specifications:
                description_lines.append(
                    f"  {item.specifications}"
                )

        production_job = ProductionService.create_job(
            order=order,
            product=product,
            job_type=job_type,
            quantity_to_produce=quantity_to_produce,
            assigned_to=None,
            created_by=cls._employee(actor),
            description="\n".join(
                description_lines
            ),
            expected_end_date=(
                order.expected_delivery_date
            ),
        )

        return production_job, True

    @classmethod
    def _route_inventory_fulfilment(
        cls,
        *,
        order,
        actor=None,
        warehouse_code,
        route_code,
    ):
        warehouse = (
            Warehouse.objects
            .filter(
                code=warehouse_code,
                is_active=True,
            )
            .first()
        )

        if warehouse is None:
            raise ValidationError(
                (
                    f"Active warehouse {warehouse_code} "
                    "was not found."
                )
            )

        fulfilment_result = (
            InventoryFulfilmentService.prepare_order(
                order=order,
                warehouse=warehouse,
                actor=actor,
                note=(
                    f"Automatically prepared during "
                    f"routing of order "
                    f"{order.order_number}."
                ),
                strict=False,
            )
        )

        return {
            "business_unit": order.business_unit,
            "route": route_code,
            "object": warehouse,
            "created": bool(
                fulfilment_result["reservations"]
            ),
            "message": (
                f"Order {order.order_number} was routed "
                f"to inventory fulfilment at "
                f"{warehouse.name}. "
                f"Reservation status: "
                f"{fulfilment_result['status']}."
            ),
            "fulfilment_result": fulfilment_result,
        }
