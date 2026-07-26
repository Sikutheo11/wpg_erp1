from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.event_engine import EventEngine

from ..models import Payable, Payment
from .account_service import AccountService
from .expense_service import ExpenseService


class PayableService:
    """
    Business logic for supplier payables and supplier payments.

    Responsibilities
    ----------------
    - create supplier payables;
    - calculate outstanding balances;
    - update payable status;
    - record partial and full supplier payments;
    - decrease the selected finance account;
    - create Expense and Transaction records;
    - prevent overpayment.
    """

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0))

    @staticmethod
    def _user(actor):
        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(actor, "user", None)

    @staticmethod
    def _status_values():
        field = Payable._meta.get_field(
            "status"
        )

        return {
            value
            for value, label in field.choices
        }

    @classmethod
    def _resolve_status(
        cls,
        *,
        total_amount,
        amount_paid,
        due_date=None,
    ):
        total_amount = cls._decimal(
            total_amount
        )

        amount_paid = cls._decimal(
            amount_paid
        )

        balance = total_amount - amount_paid

        candidates = cls._status_values()

        if balance <= 0:
            for value in (
                "paid",
                "PAID",
            ):
                if value in candidates:
                    return value

        if amount_paid > 0:
            for value in (
                "partial",
                "PARTIAL",
            ):
                if value in candidates:
                    return value

        if (
            due_date
            and due_date < timezone.localdate()
        ):
            for value in (
                "overdue",
                "OVERDUE",
            ):
                if value in candidates:
                    return value

        for value in (
            "unpaid",
            "UNPAID",
            "pending",
            "PENDING",
        ):
            if value in candidates:
                return value

        if candidates:
            return next(iter(candidates))

        return "unpaid"

    @classmethod
    def _validate_payable(cls, payable):
        if payable is None:
            raise ValidationError(
                "Payable is required."
            )

        if not isinstance(
            payable,
            Payable,
        ):
            raise ValidationError(
                "A valid Payable instance is required."
            )

        return payable

    @classmethod
    def total_paid(
        cls,
        *,
        payable,
    ):
        cls._validate_payable(
            payable
        )

        total = (
            Payment.objects
            .filter(
                payable=payable,
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
    def balance(
        cls,
        *,
        payable,
    ):
        cls._validate_payable(
            payable
        )

        return (
            cls._decimal(
                payable.total_amount
            )
            - cls._decimal(
                payable.amount_paid
            )
        )

    @classmethod
    @transaction.atomic
    def create_payable(
        cls,
        *,
        supplier,
        reference,
        total_amount,
        due_date,
        actor=None,
    ):
        if supplier is None:
            raise ValidationError(
                "Supplier is required."
            )

        reference = (
            reference or ""
        ).strip()

        if not reference:
            raise ValidationError(
                "Payable reference is required."
            )

        total_amount = cls._decimal(
            total_amount
        )

        if total_amount <= 0:
            raise ValidationError(
                "Payable total must be greater than zero."
            )

        if due_date is None:
            raise ValidationError(
                "Due date is required."
            )

        if Payable.objects.filter(
            reference=reference
        ).exists():
            raise ValidationError(
                "A payable with this reference already exists."
            )

        status = cls._resolve_status(
            total_amount=total_amount,
            amount_paid=0,
            due_date=due_date,
        )

        payable = Payable.objects.create(
            supplier=supplier,
            reference=reference,
            total_amount=total_amount,
            amount_paid=Decimal("0.00"),
            due_date=due_date,
            status=status,
        )

        EventEngine.dispatch(
            event_code="FINANCE_PAYABLE_CREATED",
            actor=cls._user(actor),
            obj=payable,
            title="Supplier Payable Created",
            message=(
                f"Payable {payable.reference} "
                f"was created for {payable.total_amount} RWF."
            ),
            level="INFO",
            metadata={
                "payable_id": payable.pk,
                "supplier_id": payable.supplier_id,
                "reference": payable.reference,
                "total_amount": str(
                    payable.total_amount
                ),
                "amount_paid": str(
                    payable.amount_paid
                ),
                "due_date": (
                    payable.due_date.isoformat()
                ),
                "status": payable.status,
            },
            notify_groups=[
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return payable

    @classmethod
    @transaction.atomic
    def refresh_status(
        cls,
        *,
        payable,
        actor=None,
    ):
        cls._validate_payable(
            payable
        )

        total_amount = cls._decimal(
            payable.total_amount
        )

        amount_paid = cls._decimal(
            payable.amount_paid
        )

        if total_amount < 0:
            raise ValidationError(
                "Payable total cannot be negative."
            )

        if amount_paid < 0:
            raise ValidationError(
                "Amount paid cannot be negative."
            )

        if amount_paid > total_amount:
            raise ValidationError(
                (
                    "Amount paid cannot exceed "
                    "the payable total."
                )
            )

        new_status = cls._resolve_status(
            total_amount=total_amount,
            amount_paid=amount_paid,
            due_date=payable.due_date,
        )

        if payable.status != new_status:
            payable.status = new_status

            payable.save(
                update_fields=[
                    "status",
                ]
            )

        return payable

    @classmethod
    @transaction.atomic
    def record_payment(
        cls,
        *,
        payable,
        account,
        amount,
        method,
        notes="",
        payment_date=None,
        actor=None,
        expense_type="purchase",
        allow_negative=False,
    ):
        cls._validate_payable(
            payable
        )

        AccountService.validate_account(
            account
        )

        amount = cls._decimal(
            amount
        )

        if amount <= 0:
            raise ValidationError(
                "Payment amount must be greater than zero."
            )

        current_paid = cls.total_paid(
            payable=payable
        )

        outstanding_balance = (
            cls._decimal(
                payable.total_amount
            )
            - current_paid
        )

        if amount > outstanding_balance:
            raise ValidationError(
                (
                    "Payment cannot exceed the "
                    f"outstanding balance of {outstanding_balance}."
                )
            )

        valid_methods = {
            value
            for value, label in (
                Payment._meta.get_field(
                    "method"
                ).choices
            )
        }

        if (
            valid_methods
            and method not in valid_methods
        ):
            raise ValidationError(
                "Invalid payment method."
            )

        payment = Payment.objects.create(
            amount=amount,
            method=method,
            receivable=None,
            payable=payable,
            date=(
                payment_date
                or timezone.localdate()
            ),
            notes=(
                notes or ""
            ).strip(),
        )

        expense_result = (
            ExpenseService.create_expense(
                account=account,
                title=(
                    f"Payment for payable "
                    f"{payable.reference}"
                ),
                expense_type=expense_type,
                amount=amount,
                supplier=payable.supplier,
                expense_date=payment.date,
                reference=(
                    f"PAYMENT-{payment.pk}"
                ),
                actor=actor,
                post_to_account=True,
                allow_negative=allow_negative,
            )
        )

        payable.amount_paid = cls.total_paid(
            payable=payable
        )

        payable.save(
            update_fields=[
                "amount_paid",
            ]
        )

        cls.refresh_status(
            payable=payable,
            actor=actor,
        )

        payable.refresh_from_db()

        EventEngine.dispatch(
            event_code="FINANCE_PAYABLE_PAYMENT_RECORDED",
            actor=cls._user(actor),
            obj=payment,
            title="Supplier Payment Recorded",
            message=(
                f"Payment of {payment.amount} RWF "
                f"was recorded for payable "
                f"{payable.reference}."
            ),
            level="SUCCESS",
            metadata={
                "payment_id": payment.pk,
                "payable_id": payable.pk,
                "supplier_id": payable.supplier_id,
                "account_id": account.pk,
                "expense_id": (
                    expense_result["expense"].pk
                ),
                "transaction_id": (
                    expense_result["transaction"].pk
                    if expense_result["transaction"]
                    else None
                ),
                "amount": str(
                    payment.amount
                ),
                "method": payment.method,
                "amount_paid": str(
                    payable.amount_paid
                ),
                "balance": str(
                    cls.balance(
                        payable=payable
                    )
                ),
                "status": payable.status,
            },
            notify_groups=[
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return {
            "payment": payment,
            "payable": payable,
            "expense": expense_result[
                "expense"
            ],
            "account": expense_result[
                "account"
            ],
            "transaction": expense_result[
                "transaction"
            ],
        }

    @classmethod
    @transaction.atomic
    def refresh_amount_paid(
        cls,
        *,
        payable,
        actor=None,
    ):
        cls._validate_payable(
            payable
        )

        payable.amount_paid = cls.total_paid(
            payable=payable
        )

        if (
            payable.amount_paid
            > cls._decimal(
                payable.total_amount
            )
        ):
            raise ValidationError(
                (
                    "Recorded payments exceed "
                    "the payable total."
                )
            )

        payable.save(
            update_fields=[
                "amount_paid",
            ]
        )

        cls.refresh_status(
            payable=payable,
            actor=actor,
        )

        payable.refresh_from_db()

        return payable

    @classmethod
    @transaction.atomic
    def mark_overdue_payables(
        cls,
        *,
        actor=None,
    ):
        today = timezone.localdate()

        status_values = cls._status_values()

        unpaid_values = [
            value
            for value in (
                "unpaid",
                "UNPAID",
                "partial",
                "PARTIAL",
                "pending",
                "PENDING",
            )
            if value in status_values
        ]

        overdue_value = next(
            (
                value
                for value in (
                    "overdue",
                    "OVERDUE",
                )
                if value in status_values
            ),
            None,
        )

        if overdue_value is None:
            return []

        queryset = Payable.objects.filter(
            due_date__lt=today,
        )

        if unpaid_values:
            queryset = queryset.filter(
                status__in=unpaid_values,
            )

        updated = []

        for payable in queryset:
            payable.status = overdue_value
            payable.save(
                update_fields=[
                    "status",
                ]
            )

            updated.append(
                payable
            )

        if updated:
            EventEngine.dispatch(
                event_code=(
                    "FINANCE_PAYABLES_MARKED_OVERDUE"
                ),
                actor=cls._user(actor),
                obj=updated[0],
                title="Payables Marked Overdue",
                message=(
                    f"{len(updated)} payable(s) "
                    "were marked overdue."
                ),
                level="WARNING",
                metadata={
                    "payable_ids": [
                        payable.pk
                        for payable in updated
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
