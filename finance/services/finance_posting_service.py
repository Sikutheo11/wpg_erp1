from django.core.exceptions import ValidationError
from django.db import transaction

from core.event_engine import EventEngine

from ..models import Payment
from .account_service import AccountService
from .income_service import IncomeService


class FinancePostingService:
    """
    Coordinates finance posting for recorded receivable payments.

    Account creation, balance updates, income creation and ledger
    transactions are delegated to AccountService and IncomeService.
    """

    @staticmethod
    def _user(actor):
        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(actor, "user", None)

    @staticmethod
    def _payment_reference(payment):
        return f"PAYMENT-{payment.pk}"

    @classmethod
    def _validate_receivable_payment(cls, payment):
        if payment is None:
            raise ValidationError(
                "Payment is required."
            )

        if not isinstance(payment, Payment):
            raise ValidationError(
                "A valid Payment instance is required."
            )

        if payment.receivable_id is None:
            raise ValidationError(
                (
                    "This posting flow requires a payment "
                    "linked to a receivable."
                )
            )

        if payment.payable_id is not None:
            raise ValidationError(
                (
                    "A payment cannot be linked to both "
                    "a receivable and a payable."
                )
            )

        if payment.amount <= 0:
            raise ValidationError(
                "Payment amount must be greater than zero."
            )

    @classmethod
    def is_receivable_payment_posted(cls, payment):
        reference = cls._payment_reference(payment)

        return IncomeService.is_duplicate_reference(
            reference=reference
        )

    @classmethod
    @transaction.atomic
    def post_receivable_payment(
        cls,
        *,
        payment,
        actor=None,
    ):
        cls._validate_receivable_payment(payment)

        if cls.is_receivable_payment_posted(payment):
            raise ValidationError(
                "This payment has already been posted."
            )

        account, account_created = (
            AccountService.get_account_for_payment_method(
                method=payment.method,
                actor=actor,
            )
        )

        income_result = (
            IncomeService.record_customer_payment_income(
                payment=payment,
                account=account,
                actor=actor,
            )
        )

        EventEngine.dispatch(
            event_code="FINANCE_PAYMENT_POSTED",
            actor=cls._user(actor),
            obj=payment,
            title="Payment Posted to Finance",
            message=(
                f"Payment #{payment.pk} of "
                f"{payment.amount} RWF was posted "
                f"to {account.name}."
            ),
            level="SUCCESS",
            metadata={
                "payment_id": payment.pk,
                "receivable_id": payment.receivable_id,
                "order_id": (
                    payment.receivable.order_id
                    if hasattr(
                        payment.receivable,
                        "order_id",
                    )
                    else None
                ),
                "account_id": account.pk,
                "account_name": account.name,
                "account_created": account_created,
                "income_id": income_result["income"].pk,
                "transaction_id": (
                    income_result["transaction"].pk
                    if income_result["transaction"]
                    else None
                ),
                "amount": str(payment.amount),
                "method": payment.method,
                "posting_date": (
                    payment.date.isoformat()
                ),
                "account_balance": str(
                    income_result["account"].balance
                ),
            },
            notify_groups=[
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return {
            "payment": payment,
            "account": income_result["account"],
            "income": income_result["income"],
            "transaction": income_result["transaction"],
            "account_created": account_created,
            "message": (
                f"Payment {payment.pk} "
                "posted successfully."
            ),
        }
