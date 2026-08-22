from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from ..identity import (
    normalize_bank_account,
    normalize_rwanda_phone,
)
from ..models import Counterparty


class CounterpartyService:
    """
    Business logic for identifying and creating counterparties.

    A counterparty must be identified before a receivable or
    payable can be recorded.
    """

    @staticmethod
    def find_by_phone(phone):
        """
        Find an existing counterparty regardless of how a Rwanda
        telephone number was formatted.
        """
        unused_phone, phone_identity = (
            normalize_rwanda_phone(phone)
        )

        return (
            Counterparty.objects
            .select_related(
                "sales_customer",
                "inventory_supplier",
            )
            .filter(
                phone_identity=phone_identity,
            )
            .first()
        )

    @staticmethod
    def find_by_bank_account(bank_account_number):
        bank_identity = normalize_bank_account(
            bank_account_number
        )

        if not bank_identity:
            return None

        return (
            Counterparty.objects
            .select_related(
                "sales_customer",
                "inventory_supplier",
            )
            .filter(
                bank_account_identity=bank_identity,
            )
            .first()
        )

    @classmethod
    def create_counterparty(
        cls,
        *,
        name,
        phone,
        party_type=Counterparty.INDIVIDUAL,
        email="",
        address="",
        tax_number="",
        bank_name="",
        bank_account_name="",
        bank_account_number="",
        is_customer=False,
        is_supplier=False,
        sales_customer=None,
        inventory_supplier=None,
    ):
        normalized_phone, phone_identity = (
            normalize_rwanda_phone(phone)
        )

        existing_by_phone = (
            Counterparty.objects
            .filter(
                phone_identity=phone_identity,
            )
            .first()
        )

        if existing_by_phone is not None:
            raise ValidationError(
                {
                    "phone": (
                        "This telephone number already belongs "
                        f"to {existing_by_phone.name}. Select the "
                        "existing record instead of creating a new one."
                    )
                }
            )

        bank_identity = normalize_bank_account(
            bank_account_number
        )

        if bank_identity:
            existing_by_bank = (
                Counterparty.objects
                .filter(
                    bank_account_identity=bank_identity,
                )
                .first()
            )

            if existing_by_bank is not None:
                raise ValidationError(
                    {
                        "bank_account_number": (
                            "This bank account already belongs "
                            f"to {existing_by_bank.name}. Select the "
                            "existing record instead of creating a new one."
                        )
                    }
                )

        counterparty = Counterparty(
            name=(name or "").strip(),
            phone=normalized_phone,
            phone_identity=phone_identity,
            party_type=party_type,
            email=(email or "").strip(),
            address=(address or "").strip(),
            tax_number=(tax_number or "").strip(),
            bank_name=(bank_name or "").strip(),
            bank_account_name=(
                bank_account_name or ""
            ).strip(),
            bank_account_number=(
                bank_account_number or ""
            ).strip(),
            bank_account_identity=bank_identity,
            is_customer=bool(is_customer),
            is_supplier=bool(is_supplier),
            sales_customer=sales_customer,
            inventory_supplier=inventory_supplier,
        )

        counterparty.full_clean()

        try:
            with transaction.atomic():
                counterparty.save(
                    force_insert=True,
                )
        except IntegrityError as error:
            raise ValidationError(
                (
                    "This person or company was registered by "
                    "another request. Search by telephone and "
                    "select the existing record."
                )
            ) from error

        return counterparty