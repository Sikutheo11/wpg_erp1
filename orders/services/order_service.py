from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone

from core.event_engine import EventEngine

from ..models import Order, OrderItem


class OrderService:
    """
    Enterprise order business logic.

    Responsibilities:
    - create orders
    - recalculate totals
    - submit and confirm orders
    - mark orders in production or ready
    - deliver, complete, and cancel orders
    """

    CUSTOMER_REQUIRED_TYPES = {
        "ECOMMERCE",
        "CUSTOM_FURNITURE",
        "CUSTOM_ORDER",
        "PROJECT",
        "MAINTENANCE",
    }

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0))

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

    @classmethod
    def _ensure_new_product_catalog_entry(cls, *, order, costing):
        """Create and link one unpublished catalogue product idempotently."""
        if order.order_type != "NEW_PRODUCT":
            return None

        item = order.items.order_by("id").first()
        if item is None:
            raise ValidationError("New Product Development requires an order item.")
        if item.product_id:
            return item.product

        from inventory.models import Product

        product = Product.objects.create(
            business_unit=order.business_unit,
            product_type="FINISHED_GOOD",
            name=(item.product_name or "New Product").strip(),
            description=(item.specifications or order.notes or "").strip(),
            unit="pcs",
            selling_price=costing.expected_selling_price,
            standard_cost=costing.total_cost,
            track_inventory=True,
            is_active=False,
            is_published=False,
            image=item.reference_image if item.reference_image else None,
        )
        item.product = product
        item.save(update_fields=["product"])
        return product

    @staticmethod
    def _choice_values(model, field_name):
        """
        Read choice values directly from the model field.
        """

        field = model._meta.get_field(field_name)

        return {
            value
            for value, label in field.choices
        }

    @classmethod
    def _validate_business_unit_and_type(
        cls,
        *,
        business_unit,
        order_type,
    ):
        valid_business_units = cls._choice_values(
            Order,
            "business_unit",
        )

        if business_unit not in valid_business_units:
            raise ValidationError(
                "Invalid business unit."
            )

        valid_order_types = cls._choice_values(
            Order,
            "order_type",
        )

        if order_type not in valid_order_types:
            raise ValidationError(
                "Invalid order type."
            )

    @classmethod
    @transaction.atomic
    def create_order(
        cls,
        *,
        business_unit,
        order_type,
        user=None,
        customer_name="",
        customer_phone="",
        customer_email="",
        province="",
        district="",
        sector="",
        cell="",
        village="",
        delivery_address="",
        notes="",
        discount=Decimal("0.00"),
        tax=Decimal("0.00"),
        expected_delivery_date=None,
    ):
        cls._validate_business_unit_and_type(
            business_unit=business_unit,
            order_type=order_type,
        )

        customer_name = (
            customer_name or ""
        ).strip()

        customer_phone = (
            customer_phone or ""
        ).strip()

        if order_type in cls.CUSTOMER_REQUIRED_TYPES:
            if not customer_name:
                raise ValidationError(
                    "Customer name is required."
                )

            if not customer_phone:
                raise ValidationError(
                    "Customer phone is required."
                )

        discount = cls._decimal(discount)
        tax = cls._decimal(tax)

        if discount < 0:
            raise ValidationError(
                "Discount cannot be negative."
            )

        if tax < 0:
            raise ValidationError(
                "Tax cannot be negative."
            )

        order = Order.objects.create(
            user=cls._user(user),
            business_unit=business_unit,
            order_type=order_type,
            status="DRAFT",
            payment_status="UNPAID",
            delivery_status="NOT_STARTED",
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email or "",
            province=province or "",
            district=district or "",
            sector=sector or "",
            cell=cell or "",
            village=village or "",
            delivery_address=delivery_address or "",
            notes=notes or "",
            subtotal=Decimal("0.00"),
            discount=discount,
            tax=tax,
            total_amount=Decimal("0.00"),
            expected_delivery_date=expected_delivery_date,
        )

        EventEngine.dispatch(
            event_code="ORDER_CREATED",
            actor=cls._user(user),
            obj=order,
            title="Order Created",
            message=(
                f"Order {order.order_number} was created."
            ),
            level="INFO",
            metadata={
                "order_id": order.pk,
                "order_number": order.order_number,
                "business_unit": order.business_unit,
                "order_type": order.order_type,
                "status": order.status,
            },
            notify_groups=[
                "Sales Manager",
                "Order Manager",
            ],
            notify_owner=True,
        )

        return order

    @classmethod
    @transaction.atomic
    def recalculate_totals(cls, order):
        if order is None:
            raise ValidationError(
                "Order is required."
            )

        item_total_expression = ExpressionWrapper(
            F("quantity") * F("price"),
            output_field=DecimalField(
                max_digits=18,
                decimal_places=2,
            ),
        )

        subtotal = (
            OrderItem.objects
            .filter(order=order)
            .aggregate(
                total=Sum(item_total_expression)
            )
            .get("total")
            or Decimal("0.00")
        )

        discount = cls._decimal(
            order.discount
        )

        tax = cls._decimal(
            order.tax
        )

        total_amount = (
            subtotal
            - discount
            + tax
        )

        if total_amount < 0:
            total_amount = Decimal("0.00")

        order.subtotal = subtotal
        order.total_amount = total_amount

        order.save(
            update_fields=[
                "subtotal",
                "total_amount",
                "updated_at",
            ]
        )

        return order

    @classmethod
    @transaction.atomic
    def submit(
        cls,
        *,
        order,
        actor=None,
    ):
        if order.status != "DRAFT":
            raise ValidationError(
                "Only draft orders can be submitted."
            )

        if not order.items.exists():
            raise ValidationError(
                "Add at least one item before submitting the order."
            )

        cls.recalculate_totals(
            order
        )

        if (
            order.business_unit == "FURNITURE"
            and order.order_type in {
                "CUSTOM_FURNITURE",
                "RESTOCK",
                "NEW_PRODUCT",
            }
        ):
            order.status = "AWAITING_QUOTATION"
        else:
            order.status = "PENDING"

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        cls._dispatch_status_event(
            order=order,
            actor=actor,
            event_code="ORDER_SUBMITTED",
            title="Order Submitted",
        )

        return order

    @classmethod
    @transaction.atomic
    def authorize_for_production(
        cls,
        *,
        order,
        actor=None,
        customer_quotation=None,
        production_costing=None,
    ):
        if order.business_unit != "FURNITURE":
            raise ValidationError("Only Furniture orders enter this production workflow.")

        if order.requires_customer_quotation:
            if customer_quotation is None or customer_quotation.status not in {"approved", "converted"}:
                raise ValidationError("The customer quotation must be approved first.")
            order.customer_quotation = customer_quotation
            order.subtotal = customer_quotation.subtotal
            order.discount = customer_quotation.discount
            order.tax = customer_quotation.tax
            order.total_amount = customer_quotation.total_amount

        elif order.requires_internal_costing:
            if production_costing is None or production_costing.status != "APPROVED":
                raise ValidationError("The internal production costing must be approved first.")
            order.production_costing = production_costing
            cls._ensure_new_product_catalog_entry(
                order=order,
                costing=production_costing,
            )

        else:
            raise ValidationError("This order type does not require a Furniture production authorization.")

        order.status = "READY_FOR_PRODUCTION"
        order.production_authorized_by = cls._user(actor)
        order.production_authorized_at = timezone.now()
        order.save()

        cls._dispatch_status_event(
            order=order,
            actor=actor,
            event_code="ORDER_READY_FOR_PRODUCTION",
            title="Order Ready for Production",
        )
        return order

    @classmethod
    @transaction.atomic
    def confirm(
        cls,
        *,
        order,
        actor=None,
    ):
        if order.status != "PENDING":
            raise ValidationError(
                "Only pending orders can be confirmed."
            )

        order.status = "CONFIRMED"

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        cls._dispatch_status_event(
            order=order,
            actor=actor,
            event_code="ORDER_CONFIRMED",
            title="Order Confirmed",
        )

        from .order_routing_service import (
            OrderRoutingService,
        )

        routing_result = (
            OrderRoutingService.route_confirmed_order(
                order=order,
                actor=actor,
            )
        )

        return order, routing_result

    @classmethod
    @transaction.atomic
    def mark_processing(
        cls,
        *,
        order,
        actor=None,
    ):
        if order.status != "CONFIRMED":
            raise ValidationError(
                "Only confirmed orders can start processing."
            )

        order.status = "PROCESSING"

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        cls._dispatch_status_event(
            order=order,
            actor=actor,
            event_code="ORDER_PROCESSING",
            title="Order Processing Started",
        )

        return order

    @classmethod
    @transaction.atomic
    def mark_in_production(
        cls,
        *,
        order,
        actor=None,
    ):
        if order.status not in {
            "CONFIRMED",
            "PROCESSING",
        }:
            raise ValidationError(
                (
                    "Only confirmed or processing orders "
                    "can enter production."
                )
            )

        order.status = "IN_PRODUCTION"

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        cls._dispatch_status_event(
            order=order,
            actor=actor,
            event_code="ORDER_IN_PRODUCTION",
            title="Order In Production",
        )

        return order

    @classmethod
    @transaction.atomic
    def mark_ready(
        cls,
        *,
        order,
        actor=None,
    ):
        if order.status not in {
            "CONFIRMED",
            "PROCESSING",
            "IN_PRODUCTION",
        }:
            raise ValidationError(
                (
                    "This order cannot be marked ready "
                    "from its current status."
                )
            )

        order.status = "READY"
        order.delivery_status = "PENDING"

        order.save(
            update_fields=[
                "status",
                "delivery_status",
                "updated_at",
            ]
        )

        cls._dispatch_status_event(
            order=order,
            actor=actor,
            event_code="ORDER_READY",
            title="Order Ready",
        )

        return order

    @classmethod
    @transaction.atomic
    def mark_shipped(
        cls,
        *,
        order,
        actor=None,
    ):
        if order.status != "READY":
            raise ValidationError(
                "Only ready orders can be shipped."
            )

        order.delivery_status = "SHIPPED"

        order.save(
            update_fields=[
                "delivery_status",
                "updated_at",
            ]
        )

        cls._dispatch_status_event(
            order=order,
            actor=actor,
            event_code="ORDER_SHIPPED",
            title="Order Shipped",
        )

        return order

    @classmethod
    @transaction.atomic
    def deliver(
        cls,
        *,
        order,
        delivered_by=None,
    ):
        if order.status != "READY":
            raise ValidationError(
                "Only ready orders can be delivered."
            )

        order.status = "DELIVERED"
        order.delivery_status = "DELIVERED"
        order.delivered_at = timezone.now()
        order.delivered_by = cls._employee(
            delivered_by
        )

        order.save(
            update_fields=[
                "status",
                "delivery_status",
                "delivered_at",
                "delivered_by",
                "updated_at",
            ]
        )

        cls._dispatch_status_event(
            order=order,
            actor=delivered_by,
            event_code="ORDER_DELIVERED",
            title="Order Delivered",
        )

        return order

    @classmethod
    @transaction.atomic
    def complete(
        cls,
        *,
        order,
        actor=None,
    ):
        if order.status != "DELIVERED":
            raise ValidationError(
                "Only delivered orders can be completed."
            )

        order.status = "COMPLETED"

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        cls._dispatch_status_event(
            order=order,
            actor=actor,
            event_code="ORDER_COMPLETED",
            title="Order Completed",
        )

        return order

    @classmethod
    @transaction.atomic
    def cancel(
        cls,
        *,
        order,
        actor=None,
        reason="",
    ):
        if order is None or not getattr(order, "pk", None):
            raise ValidationError(
                "A saved order is required."
            )

        order = (
            Order.objects
            .select_for_update()
            .get(pk=order.pk)
        )

        if order.status in {
            "DELIVERED",
            "COMPLETED",
            "CANCELLED",
        }:
            raise ValidationError(
                "This order can no longer be cancelled."
            )

        reason = (reason or "").strip()

        if not reason:
            reason = "Order cancelled by authorized staff."

        released_reservations = []
        cancelled_payments = []
        reversed_marketplace_lines = 0
        checkout = None

        if order.order_type == "ECOMMERCE":
            from ecommerce.models import (
                EcommerceCheckout,
                EcommerceCheckoutOrder,
                EcommercePayment,
                MarketplaceOrderLine,
            )
            from ecommerce.services.payment_service import (
                EcommercePaymentService,
            )

            checkout_link = (
                EcommerceCheckoutOrder.objects
                .select_related("checkout")
                .select_for_update()
                .filter(order=order)
                .first()
            )

            if checkout_link is None:
                raise ValidationError(
                    (
                        f"Ecommerce order {order.order_number} "
                        "has no checkout link."
                    )
                )

            checkout = (
                EcommerceCheckout.objects
                .select_for_update()
                .get(pk=checkout_link.checkout_id)
            )

            confirmed_payment_exists = (
                EcommercePayment.objects
                .filter(
                    checkout=checkout,
                    status=EcommercePayment.CONFIRMED,
                )
                .exists()
            )

            if (
                order.payment_status == "PAID"
                or confirmed_payment_exists
            ):
                raise ValidationError(
                    (
                        f"Paid Ecommerce order {order.order_number} "
                        "cannot be cancelled directly. Refund the "
                        "customer payment first."
                    )
                )

            active_sibling_exists = (
                EcommerceCheckoutOrder.objects
                .filter(checkout=checkout)
                .exclude(order=order)
                .exclude(order__status="CANCELLED")
                .exists()
            )

            if active_sibling_exists:
                raise ValidationError(
                    (
                        "This checkout contains multiple active orders. "
                        "Cancelling only one order would make the checkout "
                        "payment total incorrect. Cancel the complete "
                        "checkout instead."
                    )
                )

            marketplace_lines = (
                MarketplaceOrderLine.objects
                .select_for_update()
                .filter(order_item__order=order)
            )

            protected_marketplace_line_exists = (
                marketplace_lines
                .filter(
                    settlement_status__in={
                        "IN_SETTLEMENT",
                        "SETTLED",
                    }
                )
                .exists()
            )

            if protected_marketplace_line_exists:
                raise ValidationError(
                    (
                        "This order has Marketplace sale lines already "
                        "included in or paid through a seller settlement."
                    )
                )

            pending_payments = list(
                EcommercePayment.objects
                .select_for_update()
                .filter(
                    checkout=checkout,
                    status__in={
                        EcommercePayment.INITIATED,
                        EcommercePayment.PENDING,
                    },
                )
                .order_by("pk")
            )

            for payment in pending_payments:
                payment, changed = (
                    EcommercePaymentService.cancel_payment(
                        payment=payment,
                        reason=(
                            f"Order {order.order_number} cancelled. "
                            f"{reason}"
                        ),
                        actor=actor,
                    )
                )

                if changed:
                    cancelled_payments.append(payment)

            reversed_marketplace_lines = (
                marketplace_lines
                .filter(
                    settlement_status__in={
                        "UNSETTLED",
                        "ELIGIBLE",
                    }
                )
                .update(
                    settlement_status="REVERSED",
                    eligible_at=None,
                )
            )

            checkout.status = "CANCELLED"
            checkout.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        from inventory.services.reservation_service import (
            ReservationService,
        )

        release_result = (
            ReservationService.release_order_reservations(
                order=order,
                actor=actor,
                note=(
                    f"Released because order "
                    f"{order.order_number} was cancelled. "
                    f"{reason}"
                ),
            )
        )

        released_reservations = release_result["released"]

        existing_notes = (order.notes or "").strip()
        cancellation_note = f"Cancellation reason: {reason}"

        order.notes = (
            f"{existing_notes}\n{cancellation_note}"
            if existing_notes
            else cancellation_note
        )

        order.status = "CANCELLED"

        order.save(
            update_fields=[
                "status",
                "notes",
                "updated_at",
            ]
        )

        cls._dispatch_status_event(
            order=order,
            actor=actor,
            event_code="ORDER_CANCELLED",
            title="Order Cancelled",
            metadata={
                "reason": reason,
                "released_reservation_ids": [
                    reservation.pk
                    for reservation in released_reservations
                ],
                "cancelled_payment_ids": [
                    payment.pk
                    for payment in cancelled_payments
                ],
                "reversed_marketplace_lines": (
                    reversed_marketplace_lines
                ),
                "checkout_id": (
                    checkout.pk
                    if checkout is not None
                    else None
                ),
            },
            level="WARNING",
        )

        return order

    @classmethod
    def _dispatch_status_event(
        cls,
        *,
        order,
        actor,
        event_code,
        title,
        metadata=None,
        level="INFO",
    ):
        event_metadata = {
            "order_id": order.pk,
            "order_number": order.order_number,
            "business_unit": order.business_unit,
            "order_type": order.order_type,
            "status": order.status,
            "delivery_status": order.delivery_status,
            "payment_status": order.payment_status,
        }

        if metadata:
            event_metadata.update(
                metadata
            )

        EventEngine.dispatch(
            event_code=event_code,
            actor=cls._user(actor),
            obj=order,
            title=title,
            message=(
                f"Order {order.order_number} "
                f"is now {order.get_status_display()}."
            ),
            level=level,
            metadata=event_metadata,
            notify_groups=[
                "Sales Manager",
                "Order Manager",
            ],
            notify_owner=True,
        )
