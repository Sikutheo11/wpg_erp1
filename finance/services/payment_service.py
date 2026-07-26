from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.event_engine import EventEngine

from ..models import Payment, Receivable
from .receivable_service import ReceivableService


class PaymentService:
    """
    Finance business logic for receivable payments.

    Responsibilities:
    - record customer payments against a receivable;
    - prevent overpayment;
    - recalculate amount paid from Payment records;
    - update receivable status;
    - synchronize Order.payment_status;
    - complete a delivered order when fully paid.
    """

    PAYMENT_METHODS = {
        "cash",
        "bank",
        "mobile_money",
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
    def _valid_payment_methods(cls):
        """
        Read payment method values directly from the Payment model.
        """

        field = Payment._meta.get_field(
            "method"
        )

        choices = {
            value
            for value, label in field.choices
        }

        return choices or cls.PAYMENT_METHODS

    @classmethod
    def _validate_receivable(cls, receivable):
        if receivable is None:
            raise ValidationError(
                "Receivable is required."
            )

        if not isinstance(
            receivable,
            Receivable,
        ):
            raise ValidationError(
                "A valid receivable is required."
            )

        if receivable.status == "paid":
            raise ValidationError(
                "This receivable has already been paid."
            )

        if cls._decimal(
            receivable.total_amount
        ) <= 0:
            raise ValidationError(
                (
                    "The receivable total must be "
                    "greater than zero."
                )
            )

    @classmethod
    def _validate_payment_data(
        cls,
        *,
        receivable,
        amount,
        method,
    ):
        cls._validate_receivable(
            receivable
        )

        amount = cls._decimal(
            amount
        )

        if amount <= 0:
            raise ValidationError(
                "Payment amount must be greater than zero."
            )

        valid_methods = cls._valid_payment_methods()

        if method not in valid_methods:
            raise ValidationError(
                "Invalid payment method."
            )

        current_paid = cls.total_paid(
            receivable=receivable
        )

        balance = (
            cls._decimal(
                receivable.total_amount
            )
            - current_paid
        )

        if amount > balance:
            raise ValidationError(
                (
                    f"Payment amount cannot exceed "
                    f"the outstanding balance of {balance}."
                )
            )

        return amount

    @classmethod
    def total_paid(
        cls,
        *,
        receivable,
    ):
        """
        Calculate the authoritative paid amount from Payment records.
        """

        total = (
            Payment.objects
            .filter(
                receivable=receivable,
            )
            .aggregate(
                total=Sum("amount")
            )
            .get("total")
            or Decimal("0.00")
        )

        return cls._decimal(
            total
        )
    @classmethod
    @transaction.atomic
    def record_receivable_payment(
        cls,
        *,
        receivable,
        amount,
        method,
        payment_date=None,
        notes="",
        actor=None,
    ):
        amount = cls._validate_payment_data(
            receivable=receivable,
            amount=amount,
            method=method,
        )

        payment = Payment.objects.create(
            amount=amount,
            method=method,
            receivable=receivable,
            payable=None,
            date=(
                payment_date
                or timezone.localdate()
            ),
            notes=(
                notes or ""
            ).strip(),
        )

        # Recalculate the authoritative amount paid
        # from all payments linked to this receivable.
        receivable.amount_paid = cls.total_paid(
            receivable=receivable,
        )

        receivable.save(
            update_fields=[
                "amount_paid",
            ]
        )

        # Update receivable status, order payment status,
        # and complete the order when fully paid.
        ReceivableService.refresh_status(
            receivable=receivable,
            actor=actor,
            complete_order=True,
        )

        receivable.refresh_from_db()

        # Post payment automatically into Finance:
        # Payment → Income → Transaction → Account balance.
        from .finance_posting_service import (
            FinancePostingService,
        )

        posting_result = (
            FinancePostingService
            .post_receivable_payment(
                payment=payment,
                actor=actor,
            )
        )

        EventEngine.dispatch(
            event_code="FINANCE_RECEIVABLE_PAYMENT_RECORDED",
            actor=cls._user(actor),
            obj=payment,
            title="Customer Payment Recorded",
            message=(
                f"Payment of {payment.amount} RWF "
                f"was recorded for "
                f"{receivable.invoice_number}."
            ),
            level="SUCCESS",
            metadata={
                "payment_id": payment.pk,
                "receivable_id": receivable.pk,
                "order_id": (
                    receivable.order_id
                    if hasattr(
                        receivable,
                        "order_id",
                    )
                    else None
                ),
                "invoice_number": (
                    receivable.invoice_number
                ),
                "amount": str(
                    payment.amount
                ),
                "method": payment.method,
                "payment_date": (
                    payment.date.isoformat()
                ),
                "total_amount": str(
                    receivable.total_amount
                ),
                "amount_paid": str(
                    receivable.amount_paid
                ),
                "balance": str(
                    receivable.balance
                ),
                "receivable_status": (
                    receivable.status
                ),
                "finance_account_id": (
                    posting_result["account"].pk
                ),
                "income_id": (
                    posting_result["income"].pk
                ),
                "transaction_id": (
                    posting_result[
                        "transaction"
                    ].pk
                ),
            },
            notify_groups=[
                "Finance Manager",
                "Sales Manager",
                "Order Manager",
            ],
            notify_owner=True,
        )

        return payment

    @classmethod
    @transaction.atomic
    def refresh_receivable_total(
        cls,
        *,
        receivable,
        actor=None,
    ):
        """
        Recalculate Receivable.amount_paid from all linked payments.

        Useful after payment corrections, imports, or legacy data cleanup.
        """

        cls._validate_receivable(
            receivable
        )

        receivable.amount_paid = cls.total_paid(
            receivable=receivable
        )

        if (
            receivable.amount_paid
            > cls._decimal(
                receivable.total_amount
            )
        ):
            raise ValidationError(
                (
                    "Recorded payments exceed "
                    "the receivable total."
                )
            )

        receivable.save(
            update_fields=[
                "amount_paid",
            ]
        )

        ReceivableService.refresh_status(
            receivable=receivable,
            actor=actor,
            complete_order=True,
        )

        receivable.refresh_from_db()

        return receivable

    @classmethod
    @transaction.atomic
    def delete_receivable_payment(
        cls,
        *,
        payment,
        actor=None,
        reason="",
    ):
        """
        Delete an incorrect receivable payment and recalculate balances.

        Use this only for correcting an erroneous payment entry.
        """

        if payment is None:
            raise ValidationError(
                "Payment is required."
            )

        receivable = payment.receivable

        if receivable is None:
            raise ValidationError(
                (
                    "This payment is not linked "
                    "to a receivable."
                )
            )

        payment_id = payment.pk
        amount = payment.amount
        method = payment.method

        payment.delete()

        receivable.amount_paid = cls.total_paid(
            receivable=receivable
        )

        receivable.save(
            update_fields=[
                "amount_paid",
            ]
        )

        ReceivableService.refresh_status(
            receivable=receivable,
            actor=actor,
            complete_order=False,
        )

        order = getattr(
            receivable,
            "order",
            None,
        )

        if (
            order is not None
            and order.status == "COMPLETED"
            and receivable.status != "paid"
        ):
            order.status = "DELIVERED"

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        EventEngine.dispatch(
            event_code="FINANCE_RECEIVABLE_PAYMENT_DELETED",
            actor=cls._user(actor),
            obj=receivable,
            title="Customer Payment Deleted",
            message=(
                f"Payment #{payment_id} was deleted "
                f"from {receivable.invoice_number}."
            ),
            level="WARNING",
            metadata={
                "deleted_payment_id": payment_id,
                "receivable_id": receivable.pk,
                "invoice_number": (
                    receivable.invoice_number
                ),
                "amount": str(amount),
                "method": method,
                "reason": (
                    reason or ""
                ).strip(),
                "amount_paid": str(
                    receivable.amount_paid
                ),
                "balance": str(
                    receivable.balance
                ),
                "receivable_status": (
                    receivable.status
                ),
            },
            notify_groups=[
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return receivable
