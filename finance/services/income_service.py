from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine

from ..models import Income
from .account_service import AccountService


class IncomeService:
    """
    Business logic for income recognition and account posting.

    Responsibilities:
    - validate and create Income records;
    - increase the selected finance account;
    - create the related Transaction entry through AccountService;
    - support customer-order, direct-sale and other income sources;
    - prevent duplicate income posting when a reference is supplied.
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
        field = model._meta.get_field(
            field_name
        )

        return {
            value
            for value, label in field.choices
        }

    @classmethod
    def _resolve_income_type(
        cls,
        preferred_type=None,
    ):
        """
        Return a valid Income.income_type value.

        The supplied preferred type is used when it exists in the
        model choices. Otherwise common sales/income values are tried.
        """

        choices = cls._choice_values(
            Income,
            "income_type",
        )

        if (
            preferred_type
            and (
                not choices
                or preferred_type in choices
            )
        ):
            return preferred_type

        for candidate in (
            "sale",
            "SALE",
            "sales",
            "SALES",
            "customer_payment",
            "CUSTOMER_PAYMENT",
            "other",
            "OTHER",
        ):
            if candidate in choices:
                return candidate

        if not choices:
            return preferred_type or "sale"

        raise ValidationError(
            (
                "No supported income type is configured "
                "on Income.income_type."
            )
        )

    @classmethod
    def _validate_data(
        cls,
        *,
        account,
        title,
        amount,
    ):
        AccountService.validate_account(
            account
        )

        title = (
            title or ""
        ).strip()

        amount = cls._decimal(
            amount
        )

        if not title:
            raise ValidationError(
                "Income title is required."
            )

        if amount <= 0:
            raise ValidationError(
                "Income amount must be greater than zero."
            )

        return title, amount

    @classmethod
    def is_duplicate_reference(
        cls,
        *,
        reference,
    ):
        """
        Detect duplicate income posting using a reference stored
        in the Income title.

        This is a V1 safeguard because the current Income model has
        no dedicated external-reference field.
        """

        reference = (
            reference or ""
        ).strip()

        if not reference:
            return False

        return Income.objects.filter(
            title__contains=f"[{reference}]"
        ).exists()

    @classmethod
    @transaction.atomic
    def create_income(
        cls,
        *,
        account,
        title,
        income_type=None,
        amount,
        income_date=None,
        sale=None,
        reference="",
        actor=None,
        post_to_account=True,
    ):
        title, amount = cls._validate_data(
            account=account,
            title=title,
            amount=amount,
        )

        reference = (
            reference or ""
        ).strip()

        if (
            reference
            and cls.is_duplicate_reference(
                reference=reference
            )
        ):
            raise ValidationError(
                "This income reference has already been posted."
            )

        resolved_income_type = (
            cls._resolve_income_type(
                income_type
            )
        )

        posting_title = title

        if reference:
            posting_title = (
                f"{title} [{reference}]"
            )

        income = Income.objects.create(
            # AccountService owns automated balance posting. Creating with a
            # null relation prevents Income.save() from posting a second time.
            account=None,
            title=posting_title,
            income_type=resolved_income_type,
            amount=amount,
            sale=sale,
            date=(
                income_date
                or timezone.localdate()
            ),
        )

        account_result = {
            "account": account,
            "transaction": None,
        }

        if post_to_account:
            account_result = (
                AccountService.increase_balance(
                    account=account,
                    amount=amount,
                    description=posting_title,
                    transaction_date=(
                        income.date
                    ),
                    actor=actor,
                    create_transaction=True,
                )
            )

        Income.objects.filter(pk=income.pk).update(account=account)
        income.account = account

        EventEngine.dispatch(
            event_code="FINANCE_INCOME_CREATED",
            actor=cls._user(actor),
            obj=income,
            title="Income Recorded",
            message=(
                f"Income of {amount} RWF was recorded "
                f"under {income.title}."
            ),
            level="SUCCESS",
            metadata={
                "income_id": income.pk,
                "account_id": account.pk,
                "transaction_id": (
                    account_result[
                        "transaction"
                    ].pk
                    if account_result[
                        "transaction"
                    ]
                    else None
                ),
                "sale_id": (
                    income.sale_id
                    if hasattr(
                        income,
                        "sale_id",
                    )
                    else None
                ),
                "income_type": (
                    income.income_type
                ),
                "amount": str(
                    income.amount
                ),
                "date": (
                    income.date.isoformat()
                ),
                "reference": reference,
                "account_balance": str(
                    account_result[
                        "account"
                    ].balance
                ),
            },
            notify_groups=[
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return {
            "income": income,
            "account": account_result[
                "account"
            ],
            "transaction": account_result[
                "transaction"
            ],
        }

    @classmethod
    @transaction.atomic
    def record_customer_payment_income(
        cls,
        *,
        payment,
        account=None,
        actor=None,
    ):
        """
        Record income generated by a receivable payment.

        This method is intended for PaymentService or
        FinancePostingService integration.
        """

        if payment is None:
            raise ValidationError(
                "Payment is required."
            )

        if payment.receivable_id is None:
            raise ValidationError(
                (
                    "The payment must be linked "
                    "to a receivable."
                )
            )

        if account is None:
            account, _ = (
                AccountService
                .get_account_for_payment_method(
                    method=payment.method,
                    actor=actor,
                )
            )

        reference = (
            f"PAYMENT-{payment.pk}"
        )

        return cls.create_income(
            account=account,
            title=(
                f"Payment for "
                f"{payment.receivable.invoice_number}"
            ),
            income_type="sale",
            amount=payment.amount,
            income_date=payment.date,
            sale=None,
            reference=reference,
            actor=actor,
            post_to_account=True,
        )

    @classmethod
    @transaction.atomic
    def record_direct_income(
        cls,
        *,
        account,
        title,
        amount,
        income_type=None,
        income_date=None,
        reference="",
        actor=None,
    ):
        """
        Record income that is not linked to a customer receivable.
        """

        return cls.create_income(
            account=account,
            title=title,
            income_type=income_type,
            amount=amount,
            income_date=income_date,
            sale=None,
            reference=reference,
            actor=actor,
            post_to_account=True,
        )
