from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from core.event_engine import EventEngine

from ..models import Account, Transaction


class AccountService:
    """
    Business logic for Finance accounts and account balances.

    Responsibilities:
    - create and retrieve finance accounts;
    - create standard Cash, Bank and Mobile Money accounts;
    - increase or decrease balances safely;
    - prevent negative balances when required;
    - post account-level transactions;
    - keep account balance updates atomic.
    """

    STANDARD_ACCOUNTS = {
        "cash": {
            "name": "Cash",
            "account_number": "AUTO-CASH",
        },
        "bank": {
            "name": "Bank",
            "account_number": "AUTO-BANK",
        },
        "mobile_money": {
            "name": "Mobile Money",
            "account_number": "AUTO-MOBILE_MONEY",
        },
    }

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
    def _resolve_account_type(
        cls,
        account_kind,
    ):
        """
        Resolve a valid Account.account_type choice.

        Supports common values without tightly coupling this service
        to one exact Account model implementation.
        """

        choices = cls._choice_values(
            Account,
            "account_type",
        )

        candidates = {
            "cash": (
                "CASH",
                "cash",
                "ASSET",
                "asset",
            ),
            "bank": (
                "BANK",
                "bank",
                "ASSET",
                "asset",
            ),
            "mobile_money": (
                "MOBILE_MONEY",
                "mobile_money",
                "ASSET",
                "asset",
            ),
        }.get(
            account_kind,
            (
                "ASSET",
                "asset",
            ),
        )

        for candidate in candidates:
            if candidate in choices:
                return candidate

        if not choices:
            return "asset"

        return next(iter(choices))

    @classmethod
    def _resolve_transaction_type(
        cls,
        *,
        direction,
    ):
        """
        Resolve a valid Transaction.transaction_type choice.

        direction:
        - "IN" for money entering an account
        - "OUT" for money leaving an account
        """

        choices = cls._choice_values(
            Transaction,
            "transaction_type",
        )

        incoming_candidates = (
            "INCOME",
            "income",
            "CREDIT",
            "credit",
            "IN",
            "in",
            "DEPOSIT",
            "deposit",
            "RECEIPT",
            "receipt",
        )

        outgoing_candidates = (
            "EXPENSE",
            "expense",
            "DEBIT",
            "debit",
            "OUT",
            "out",
            "WITHDRAWAL",
            "withdrawal",
            "PAYMENT",
            "payment",
        )

        candidates = (
            incoming_candidates
            if direction == "IN"
            else outgoing_candidates
        )

        for candidate in candidates:
            if candidate in choices:
                return candidate

        if not choices:
            return (
                "income"
                if direction == "IN"
                else "expense"
            )

        raise ValidationError(
            (
                "No supported transaction type is configured "
                f"for direction {direction}."
            )
        )

    @classmethod
    def validate_account(cls, account):
        if account is None:
            raise ValidationError(
                "Account is required."
            )

        if not isinstance(
            account,
            Account,
        ):
            raise ValidationError(
                "A valid Account instance is required."
            )

        return account

    @classmethod
    @transaction.atomic
    def create_account(
        cls,
        *,
        name,
        account_type,
        account_number="",
        opening_balance=0,
        actor=None,
    ):
        name = (
            name or ""
        ).strip()

        account_number = (
            account_number or ""
        ).strip()

        opening_balance = cls._decimal(
            opening_balance
        )

        if not name:
            raise ValidationError(
                "Account name is required."
            )

        valid_account_types = cls._choice_values(
            Account,
            "account_type",
        )

        if (
            valid_account_types
            and account_type not in valid_account_types
        ):
            raise ValidationError(
                "Invalid account type."
            )

        if opening_balance < 0:
            raise ValidationError(
                "Opening balance cannot be negative."
            )

        if (
            account_number
            and Account.objects.filter(
                account_number=account_number
            ).exists()
        ):
            raise ValidationError(
                "An account with this number already exists."
            )

        account = Account.objects.create(
            name=name,
            account_type=account_type,
            account_number=account_number,
            balance=opening_balance,
        )

        EventEngine.dispatch(
            event_code="FINANCE_ACCOUNT_CREATED",
            actor=cls._user(actor),
            obj=account,
            title="Finance Account Created",
            message=(
                f"Finance account {account.name} "
                "was created."
            ),
            level="INFO",
            metadata={
                "account_id": account.pk,
                "name": account.name,
                "account_type": (
                    account.account_type
                ),
                "account_number": (
                    account.account_number
                ),
                "opening_balance": str(
                    account.balance
                ),
            },
            notify_groups=[
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return account

    @classmethod
    @transaction.atomic
    def get_or_create_standard_account(
        cls,
        *,
        account_kind,
        actor=None,
    ):
        config = cls.STANDARD_ACCOUNTS.get(
            account_kind
        )

        if config is None:
            raise ValidationError(
                "Unsupported standard account type."
            )

        account_type = cls._resolve_account_type(
            account_kind
        )

        account, created = Account.objects.get_or_create(
            name=config["name"],
            defaults={
                "account_type": account_type,
                "account_number": (
                    config["account_number"]
                ),
                "balance": Decimal("0.00"),
            },
        )

        if created:
            EventEngine.dispatch(
                event_code=(
                    "FINANCE_STANDARD_ACCOUNT_CREATED"
                ),
                actor=cls._user(actor),
                obj=account,
                title="Standard Finance Account Created",
                message=(
                    f"{account.name} account was created."
                ),
                level="INFO",
                metadata={
                    "account_id": account.pk,
                    "account_kind": account_kind,
                    "account_type": (
                        account.account_type
                    ),
                    "account_number": (
                        account.account_number
                    ),
                },
                notify_groups=[
                    "Finance Manager",
                ],
                notify_owner=True,
            )

        return account, created

    @classmethod
    def get_or_create_cash_account(
        cls,
        *,
        actor=None,
    ):
        return cls.get_or_create_standard_account(
            account_kind="cash",
            actor=actor,
        )

    @classmethod
    def get_or_create_bank_account(
        cls,
        *,
        actor=None,
    ):
        return cls.get_or_create_standard_account(
            account_kind="bank",
            actor=actor,
        )

    @classmethod
    def get_or_create_mobile_money_account(
        cls,
        *,
        actor=None,
    ):
        return cls.get_or_create_standard_account(
            account_kind="mobile_money",
            actor=actor,
        )

    @classmethod
    def get_account_for_payment_method(
        cls,
        *,
        method,
        actor=None,
    ):
        if method == "cash":
            return cls.get_or_create_cash_account(
                actor=actor
            )

        if method == "bank":
            return cls.get_or_create_bank_account(
                actor=actor
            )

        if method == "mobile_money":
            return (
                cls.get_or_create_mobile_money_account(
                    actor=actor
                )
            )

        raise ValidationError(
            "Unsupported payment method."
        )

    @classmethod
    def current_balance(
        cls,
        *,
        account,
    ):
        cls.validate_account(
            account
        )

        account.refresh_from_db(
            fields=[
                "balance",
            ]
        )

        return cls._decimal(
            account.balance
        )

    @classmethod
    def validate_sufficient_balance(
        cls,
        *,
        account,
        amount,
    ):
        cls.validate_account(
            account
        )

        amount = cls._decimal(
            amount
        )

        if amount <= 0:
            raise ValidationError(
                "Amount must be greater than zero."
            )

        balance = cls.current_balance(
            account=account
        )

        if balance < amount:
            raise ValidationError(
                (
                    f"Insufficient balance in "
                    f"{account.name}. "
                    f"Available: {balance}; "
                    f"required: {amount}."
                )
            )

        return True

    @classmethod
    @transaction.atomic
    def increase_balance(
        cls,
        *,
        account,
        amount,
        description="",
        transaction_date=None,
        actor=None,
        create_transaction=True,
    ):
        cls.validate_account(
            account
        )

        amount = cls._decimal(
            amount
        )

        if amount <= 0:
            raise ValidationError(
                "Amount must be greater than zero."
            )

        locked_account = (
            Account.objects
            .select_for_update()
            .get(pk=account.pk)
        )

        locked_account.balance = (
            cls._decimal(
                locked_account.balance
            )
            + amount
        )

        locked_account.save(
            update_fields=[
                "balance",
            ]
        )

        ledger_transaction = None

        if create_transaction:
            ledger_transaction = (
                Transaction.objects.create(
                    account=locked_account,
                    transaction_type=(
                        cls._resolve_transaction_type(
                            direction="IN"
                        )
                    ),
                    amount=amount,
                    description=(
                        description or ""
                    ).strip(),
                    date=transaction_date,
                )
            )

        EventEngine.dispatch(
            event_code=(
                "FINANCE_ACCOUNT_BALANCE_INCREASED"
            ),
            actor=cls._user(actor),
            obj=locked_account,
            title="Account Balance Increased",
            message=(
                f"{locked_account.name} increased "
                f"by {amount}."
            ),
            level="SUCCESS",
            metadata={
                "account_id": (
                    locked_account.pk
                ),
                "amount": str(amount),
                "balance": str(
                    locked_account.balance
                ),
                "transaction_id": (
                    ledger_transaction.pk
                    if ledger_transaction
                    else None
                ),
                "description": (
                    description or ""
                ).strip(),
            },
            notify_groups=[
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return {
            "account": locked_account,
            "transaction": ledger_transaction,
        }

    @classmethod
    @transaction.atomic
    def decrease_balance(
        cls,
        *,
        account,
        amount,
        description="",
        transaction_date=None,
        actor=None,
        allow_negative=False,
        create_transaction=True,
    ):
        cls.validate_account(
            account
        )

        amount = cls._decimal(
            amount
        )

        if amount <= 0:
            raise ValidationError(
                "Amount must be greater than zero."
            )

        locked_account = (
            Account.objects
            .select_for_update()
            .get(pk=account.pk)
        )

        current_balance = cls._decimal(
            locked_account.balance
        )

        if (
            not allow_negative
            and current_balance < amount
        ):
            raise ValidationError(
                (
                    f"Insufficient balance in "
                    f"{locked_account.name}. "
                    f"Available: {current_balance}; "
                    f"required: {amount}."
                )
            )

        locked_account.balance = (
            current_balance - amount
        )

        locked_account.save(
            update_fields=[
                "balance",
            ]
        )

        ledger_transaction = None

        if create_transaction:
            ledger_transaction = (
                Transaction.objects.create(
                    account=locked_account,
                    transaction_type=(
                        cls._resolve_transaction_type(
                            direction="OUT"
                        )
                    ),
                    amount=amount,
                    description=(
                        description or ""
                    ).strip(),
                    date=transaction_date,
                )
            )

        EventEngine.dispatch(
            event_code=(
                "FINANCE_ACCOUNT_BALANCE_DECREASED"
            ),
            actor=cls._user(actor),
            obj=locked_account,
            title="Account Balance Decreased",
            message=(
                f"{locked_account.name} decreased "
                f"by {amount}."
            ),
            level="WARNING",
            metadata={
                "account_id": (
                    locked_account.pk
                ),
                "amount": str(amount),
                "balance": str(
                    locked_account.balance
                ),
                "transaction_id": (
                    ledger_transaction.pk
                    if ledger_transaction
                    else None
                ),
                "description": (
                    description or ""
                ).strip(),
                "allow_negative": allow_negative,
            },
            notify_groups=[
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return {
            "account": locked_account,
            "transaction": ledger_transaction,
        }
