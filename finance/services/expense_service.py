from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine

from ..models import Expense
from .account_service import AccountService


class ExpenseService:
    """
    Business logic for recording expenses.

    Responsibilities
    ----------------
    - validate expense data;
    - create Expense records;
    - decrease the selected finance account;
    - create Transaction entries through AccountService;
    - prevent duplicate expense references.
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
    def _choice_values(model, field_name):
        field = model._meta.get_field(field_name)
        return {v for v, _ in field.choices}

    @classmethod
    def _resolve_expense_type(cls, preferred=None):
        choices = cls._choice_values(
            Expense,
            "expense_type",
        )

        if preferred and (not choices or preferred in choices):
            return preferred

        for candidate in (
            "purchase", "PURCHASE",
            "operating", "OPERATING",
            "transport", "TRANSPORT",
            "salary", "SALARY",
            "other", "OTHER",
        ):
            if candidate in choices:
                return candidate

        if not choices:
            return preferred or "other"

        return next(iter(choices))

    @classmethod
    def is_duplicate_reference(cls, reference):
        reference = (reference or "").strip()
        if not reference:
            return False
        return Expense.objects.filter(
            title__contains=f"[{reference}]"
        ).exists()

    @classmethod
    @transaction.atomic
    def create_expense(
        cls,
        *,
        account,
        title,
        amount,
        expense_type=None,
        supplier=None,
        expense_date=None,
        reference="",
        actor=None,
        post_to_account=True,
        allow_negative=False,
    ):
        AccountService.validate_account(account)

        title = (title or "").strip()
        if not title:
            raise ValidationError("Expense title is required.")

        amount = cls._decimal(amount)
        if amount <= 0:
            raise ValidationError(
                "Expense amount must be greater than zero."
            )

        reference = (reference or "").strip()

        if reference and cls.is_duplicate_reference(reference):
            raise ValidationError(
                "This expense reference has already been posted."
            )

        expense_type = cls._resolve_expense_type(expense_type)

        final_title = (
            f"{title} [{reference}]"
            if reference else title
        )

        expense = Expense.objects.create(
            # AccountService owns automated balance posting. Creating with a
            # null relation prevents Expense.save() from posting a second time.
            account=None,
            title=final_title,
            expense_type=expense_type,
            amount=amount,
            supplier=supplier,
            date=expense_date or timezone.localdate(),
        )

        account_result = {
            "account": account,
            "transaction": None,
        }

        if post_to_account:
            account_result = AccountService.decrease_balance(
                account=account,
                amount=amount,
                description=final_title,
                transaction_date=expense.date,
                actor=actor,
                allow_negative=allow_negative,
                create_transaction=True,
            )

        Expense.objects.filter(pk=expense.pk).update(account=account)
        expense.account = account

        EventEngine.dispatch(
            event_code="FINANCE_EXPENSE_CREATED",
            actor=cls._user(actor),
            obj=expense,
            title="Expense Recorded",
            message=f"Expense of {amount} recorded.",
            level="WARNING",
            metadata={
                "expense_id": expense.pk,
                "account_id": account.pk,
                "transaction_id": (
                    account_result["transaction"].pk
                    if account_result["transaction"] else None
                ),
                "supplier_id": (
                    supplier.pk if supplier else None
                ),
                "amount": str(amount),
                "expense_type": expense.expense_type,
                "reference": reference,
                "balance": str(
                    account_result["account"].balance
                ),
            },
            notify_groups=["Finance Manager"],
            notify_owner=True,
        )

        return {
            "expense": expense,
            "account": account_result["account"],
            "transaction": account_result["transaction"],
        }

    @classmethod
    @transaction.atomic
    def record_supplier_expense(
        cls,
        *,
        account,
        supplier,
        title,
        amount,
        reference="",
        actor=None,
    ):
        return cls.create_expense(
            account=account,
            supplier=supplier,
            title=title,
            amount=amount,
            expense_type="purchase",
            reference=reference,
            actor=actor,
        )

    @classmethod
    @transaction.atomic
    def record_operating_expense(
        cls,
        *,
        account,
        title,
        amount,
        reference="",
        actor=None,
    ):
        return cls.create_expense(
            account=account,
            title=title,
            amount=amount,
            expense_type="operating",
            reference=reference,
            actor=actor,
        )
