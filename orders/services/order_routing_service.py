from django.core.exceptions import ValidationError
from django.db import transaction

from core.event_engine import EventEngine

from ..models import Order


class OrderRoutingService:
    """
    Routes a confirmed enterprise order to the responsible
    business-unit workflow.

    Version 1:
    - Furniture production routing is active.
    - Construction, Agriculture and Marketplace are returned
      as pending integrations.
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
            result = {
                "business_unit": "AGRICULTURE",
                "route": "AGRICULTURE_PENDING",
                "object": None,
                "created": False,
                "message": (
                    "Agriculture fulfilment routing is not yet connected."
                ),
            }

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
            return {
                "business_unit": "FURNITURE",
                "route": "FURNITURE_FULFILMENT",
                "object": None,
                "created": False,
                "message": (
                    f"Order {order.order_number} is ready "
                    "for inventory fulfilment review."
                ),
            }

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