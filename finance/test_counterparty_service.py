from django.core.exceptions import ValidationError
from django.test import TestCase

from finance.models import Counterparty
from finance.services.counterparty_service import (
    CounterpartyService,
)


class CounterpartyServiceTests(TestCase):
    def test_find_by_phone_accepts_different_formats(self):
        counterparty = Counterparty.objects.create(
            name="Existing Person",
            phone="0788123456",
        )

        found = CounterpartyService.find_by_phone(
            "+250 788 123 456"
        )

        self.assertEqual(
            found,
            counterparty,
        )

    def test_find_by_phone_returns_none_when_not_found(self):
        found = CounterpartyService.find_by_phone(
            "0788123456"
        )

        self.assertIsNone(found)

    def test_create_counterparty_normalizes_identity(self):
        counterparty = (
            CounterpartyService.create_counterparty(
                name="New Supplier",
                phone="0788 123 456",
                bank_name="Bank of Kigali",
                bank_account_name="New Supplier",
                bank_account_number="0012-3456-7890",
                is_supplier=True,
            )
        )

        self.assertEqual(
            counterparty.phone,
            "+250788123456",
        )
        self.assertEqual(
            counterparty.phone_identity,
            "788123456",
        )
        self.assertEqual(
            counterparty.bank_account_identity,
            "001234567890",
        )
        self.assertTrue(counterparty.is_supplier)

    def test_duplicate_phone_is_rejected(self):
        Counterparty.objects.create(
            name="Existing Person",
            phone="0788123456",
        )

        with self.assertRaises(ValidationError) as context:
            CounterpartyService.create_counterparty(
                name="Duplicate Person",
                phone="+250788123456",
            )

        self.assertIn(
            "phone",
            context.exception.message_dict,
        )
        self.assertEqual(
            Counterparty.objects.count(),
            1,
        )

    def test_duplicate_bank_account_is_rejected(self):
        Counterparty.objects.create(
            name="Existing Account Holder",
            phone="0788123456",
            bank_name="Bank of Kigali",
            bank_account_number="0012 3456 7890",
        )

        with self.assertRaises(ValidationError) as context:
            CounterpartyService.create_counterparty(
                name="Duplicate Account",
                phone="0788111111",
                bank_name="Bank of Kigali",
                bank_account_number="0012-3456-7890",
            )

        self.assertIn(
            "bank_account_number",
            context.exception.message_dict,
        )
        self.assertEqual(
            Counterparty.objects.count(),
            1,
        )