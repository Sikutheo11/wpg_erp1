from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Counterparty


class CounterpartyIdentityTests(TestCase):
    def test_rwanda_phone_is_saved_in_canonical_format(self):
        counterparty = Counterparty.objects.create(
            name="Test Customer",
            phone="0788123456",
        )

        self.assertEqual(
            counterparty.phone,
            "+250788123456",
        )
        self.assertEqual(
            counterparty.phone_identity,
            "788123456",
        )

    def test_same_phone_cannot_be_registered_twice(self):
        Counterparty.objects.create(
            name="First Record",
            phone="0788123456",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Counterparty.objects.create(
                    name="Duplicate Record",
                    phone="+250788123456",
                )

        self.assertEqual(
            Counterparty.objects.count(),
            1,
        )

    def test_same_bank_account_cannot_be_registered_twice(self):
        Counterparty.objects.create(
            name="First Account Holder",
            phone="0788123456",
            bank_name="Bank of Kigali",
            bank_account_number="0012 3456 7890",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Counterparty.objects.create(
                    name="Duplicate Account Holder",
                    phone="0788111111",
                    bank_name="Bank of Kigali",
                    bank_account_number="0012-3456-7890",
                )

        self.assertEqual(
            Counterparty.objects.count(),
            1,
        )

    def test_multiple_blank_bank_accounts_are_allowed(self):
        Counterparty.objects.create(
            name="First Person",
            phone="0788123456",
        )
        Counterparty.objects.create(
            name="Second Person",
            phone="0788111111",
        )

        self.assertEqual(
            Counterparty.objects.count(),
            2,
        )

    def test_bank_account_requires_bank_name_during_validation(self):
        counterparty = Counterparty(
            name="Account Holder",
            phone="0788123456",
            bank_account_number="001234567890",
        )

        with self.assertRaises(ValidationError) as context:
            counterparty.full_clean()

        self.assertIn(
            "bank_name",
            context.exception.message_dict,
        )

    def test_invalid_phone_is_rejected(self):
        counterparty = Counterparty(
            name="Invalid Phone",
            phone="12345",
        )

        with self.assertRaises(ValidationError):
            counterparty.full_clean()