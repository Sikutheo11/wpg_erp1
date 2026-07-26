from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine

from ..models import Receivable


class ReceivableService:
    """
    Finance business logic for receivables created from customer orders.

    Responsibilities:
    - create one receivable per delivered customer order;
    - keep receivable totals synchronized with the order;
    - calculate and update receivable status;
    - synchronize Order.payment_status;
    - complete a delivered order when fully paid.
    """

    INTERNAL_ORDER_TYPES = {
        "RESTOCK",
        "NEW_PRODUCT",
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

    @classmethod
    def _validate_order_for_receivable(cls, order):
        if order is None:
            raise ValidationError(
                "Order is required."
            )

        if order.order_type in cls.INTERNAL_ORDER_TYPES:
            raise ValidationError(
                (
                    "Internal restock and new-product orders "
                    "do not create customer receivables."
                )
            )

        if order.status not in {
            "DELIVERED",
            "COMPLETED",
        }:
            raise ValidationError(
                (
                    "A receivable can only be created from "
                    "a delivered or completed order."
                )
            )

        total_amount = cls._decimal(
            order.total_amount
        )

        if total_amount <= 0:
            raise ValidationError(
                (
                    "The order total must be greater than zero "
                    "before creating a receivable."
                )
            )

    @staticmethod
    def _invoice_number(order):
        return f"INV-{order.order_number}"

    @staticmethod
    def _default_due_date(order, payment_days=30):
        base_date = (
            order.delivered_at.date()
            if order.delivered_at
            else timezone.localdate()
        )

        return base_date + timedelta(
            days=payment_days
        )

    @classmethod
    def calculate_status(cls, receivable):
        total_amount = cls._decimal(
            receivable.total_amount
        )

        amount_paid = cls._decimal(
            receivable.amount_paid
        )

        balance = total_amount - amount_paid

        if balance <= 0:
            return "paid"

        if amount_paid > 0:
            return "partial"

        if (
            receivable.due_date
            and receivable.due_date < timezone.localdate()
        ):
            return "overdue"

        return "unpaid"

    @classmethod
    @transaction.atomic
    def create_from_order(
        cls,
        *,
        order,
        due_date=None,
        payment_days=30,
        actor=None,
    ):
        cls._validate_order_for_receivable(
            order
        )

        total_amount = cls._decimal(
            order.total_amount
        )

        due_date = (
            due_date
            or cls._default_due_date(
                order,
                payment_days=payment_days,
            )
        )

        receivable, created = (
            Receivable.objects.get_or_create(
                order=order,
                defaults={
                    "customer": order.user,
                    "invoice_number": cls._invoice_number(
                        order
                    ),
                    "total_amount": total_amount,
                    "amount_paid": Decimal("0.00"),
                    "due_date": due_date,
                    "status": "unpaid",
                },
            )
        )

        if not created:
            receivable.customer = order.user
            receivable.total_amount = total_amount
            receivable.due_date = due_date
            receivable.status = cls.calculate_status(
                receivable
            )

            receivable.save(
                update_fields=[
                    "customer",
                    "total_amount",
                    "due_date",
                    "status",
                ]
            )

        order_payment_status = (
            "PAID"
            if receivable.status == "paid"
            else (
                "PARTIAL"
                if receivable.status == "partial"
                else "UNPAID"
            )
        )

        if order.payment_status != order_payment_status:
            order.payment_status = order_payment_status

            order.save(
                update_fields=[
                    "payment_status",
                    "updated_at",
                ]
            )

        EventEngine.dispatch(
            event_code="FINANCE_RECEIVABLE_CREATED",
            actor=cls._user(actor),
            obj=receivable,
            title=(
                "Receivable Created"
                if created
                else "Receivable Updated"
            ),
            message=(
                f"Receivable {receivable.invoice_number} "
                f"for order {order.order_number} "
                f"has been {'created' if created else 'updated'}."
            ),
            level="INFO",
            metadata={
                "receivable_id": receivable.pk,
                "order_id": order.pk,
                "order_number": order.order_number,
                "invoice_number": receivable.invoice_number,
                "total_amount": str(
                    receivable.total_amount
                ),
                "amount_paid": str(
                    receivable.amount_paid
                ),
                "balance": str(
                    receivable.balance
                ),
                "due_date": receivable.due_date.isoformat(),
                "status": receivable.status,
                "created": created,
            },
            notify_groups=[
                "Finance Manager",
                "Sales Manager",
                "Order Manager",
            ],
            notify_owner=True,
        )

        return receivable, created

    @classmethod
    @transaction.atomic
    def refresh_status(
        cls,
        *,
        receivable,
        actor=None,
        complete_order=True,
    ):
        if receivable is None:
            raise ValidationError(
                "Receivable is required."
            )

        total_amount = cls._decimal(
            receivable.total_amount
        )

        amount_paid = cls._decimal(
            receivable.amount_paid
        )

        if total_amount < 0:
            raise ValidationError(
                "Receivable total cannot be negative."
            )

        if amount_paid < 0:
            raise ValidationError(
                "Amount paid cannot be negative."
            )

        if amount_paid > total_amount:
            raise ValidationError(
                (
                    "Amount paid cannot exceed "
                    "the receivable total."
                )
            )

        new_status = cls.calculate_status(
            receivable
        )

        if receivable.status != new_status:
            receivable.status = new_status

            receivable.save(
                update_fields=[
                    "status",
                ]
            )

        order = getattr(
            receivable,
            "order",
            None,
        )

        if order is not None:
            if new_status == "paid":
                payment_status = "PAID"

            elif new_status == "partial":
                payment_status = "PARTIAL"

            else:
                payment_status = "UNPAID"

            order_fields = []

            if order.payment_status != payment_status:
                order.payment_status = payment_status
                order_fields.append(
                    "payment_status"
                )

            if (
                complete_order
                and new_status == "paid"
                and order.status == "DELIVERED"
            ):
                order.status = "COMPLETED"
                order_fields.append(
                    "status"
                )

            if order_fields:
                order_fields.append(
                    "updated_at"
                )

                order.save(
                    update_fields=order_fields
                )

        EventEngine.dispatch(
            event_code="FINANCE_RECEIVABLE_STATUS_UPDATED",
            actor=cls._user(actor),
            obj=receivable,
            title="Receivable Status Updated",
            message=(
                f"Receivable {receivable.invoice_number} "
                f"is now {receivable.get_status_display()}."
            ),
            level=(
                "SUCCESS"
                if new_status == "paid"
                else "INFO"
            ),
            metadata={
                "receivable_id": receivable.pk,
                "order_id": (
                    receivable.order_id
                    if hasattr(receivable, "order_id")
                    else None
                ),
                "invoice_number": receivable.invoice_number,
                "total_amount": str(
                    receivable.total_amount
                ),
                "amount_paid": str(
                    receivable.amount_paid
                ),
                "balance": str(
                    receivable.balance
                ),
                "status": new_status,
            },
            notify_groups=[
                "Finance Manager",
                "Order Manager",
            ],
            notify_owner=True,
        )

        return receivable

    @classmethod
    @transaction.atomic
    def mark_overdue_receivables(
        cls,
        *,
        actor=None,
    ):
        today = timezone.localdate()

        receivables = Receivable.objects.filter(
            due_date__lt=today,
            status__in=[
                "unpaid",
                "partial",
            ],
        )

        updated = []

        for receivable in receivables:
            receivable.status = "overdue"
            receivable.save(
                update_fields=[
                    "status",
                ]
            )

            updated.append(
                receivable
            )

        if updated:
            EventEngine.dispatch(
                event_code="FINANCE_RECEIVABLES_MARKED_OVERDUE",
                actor=cls._user(actor),
                obj=updated[0],
                title="Receivables Marked Overdue",
                message=(
                    f"{len(updated)} receivable(s) "
                    "were marked overdue."
                ),
                level="WARNING",
                metadata={
                    "receivable_ids": [
                        receivable.pk
                        for receivable in updated
                    ],
                    "count": len(updated),
                    "date": today.isoformat(),
                },
                notify_groups=[
                    "Finance Manager",
                ],
                notify_owner=False,
            )

        return updated
