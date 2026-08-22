from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from finance.models import (
    Counterparty,
    DebtLine,
    DebtRecord,
)


class DebtRecordModelTests(TestCase):
    def setUp(self):
        self.counterparty = (
            Counterparty.objects.create(
                name="Debt Test Person",
                phone="0788123456",
                is_customer=True,
                is_supplier=True,
            )
        )

    def test_reference_is_generated_automatically(self):
        debt = DebtRecord.objects.create(
            counterparty=self.counterparty,
            direction=DebtRecord.THEY_OWE_US,
        )

        self.assertTrue(
            debt.reference.startswith("DEBT-")
        )

    def test_generated_references_are_unique(self):
        first = DebtRecord.objects.create(
            counterparty=self.counterparty,
            direction=DebtRecord.THEY_OWE_US,
        )
        second = DebtRecord.objects.create(
            counterparty=self.counterparty,
            direction=DebtRecord.WE_OWE_THEM,
        )

        self.assertNotEqual(
            first.reference,
            second.reference,
        )

    def test_line_total_is_quantity_times_unit_price(self):
        debt = DebtRecord.objects.create(
            counterparty=self.counterparty,
            direction=DebtRecord.THEY_OWE_US,
        )

        line = DebtLine.objects.create(
            debt=debt,
            description="Timber",
            quantity=Decimal("2.500"),
            unit="metre",
            unit_price=Decimal("1200.00"),
        )

        self.assertEqual(
            line.line_total,
            Decimal("3000.00"),
        )

    def test_debt_total_is_sum_of_all_lines(self):
        debt = DebtRecord.objects.create(
            counterparty=self.counterparty,
            direction=DebtRecord.WE_OWE_THEM,
        )

        DebtLine.objects.create(
            debt=debt,
            description="Timber",
            quantity=Decimal("2.000"),
            unit="piece",
            unit_price=Decimal("1000.00"),
        )
        DebtLine.objects.create(
            debt=debt,
            description="Transport service",
            quantity=Decimal("1.000"),
            unit="service",
            unit_price=Decimal("5000.00"),
        )

        total = debt.recalculate_total()
        debt.refresh_from_db()

        self.assertEqual(
            total,
            Decimal("7000.00"),
        )
        self.assertEqual(
            debt.total_amount,
            Decimal("7000.00"),
        )

    def test_balance_is_total_less_amount_paid(self):
        debt = DebtRecord.objects.create(
            counterparty=self.counterparty,
            direction=DebtRecord.THEY_OWE_US,
            total_amount=Decimal("10000.00"),
            amount_paid=Decimal("2500.00"),
        )

        self.assertEqual(
            debt.balance,
            Decimal("7500.00"),
        )

    def test_due_date_cannot_precede_transaction_date(self):
        debt = DebtRecord(
            counterparty=self.counterparty,
            direction=DebtRecord.THEY_OWE_US,
            transaction_date=date(2026, 8, 21),
            due_date=date(2026, 8, 20),
        )

        with self.assertRaises(ValidationError) as context:
            debt.full_clean()

        self.assertIn(
            "due_date",
            context.exception.message_dict,
        )

    def test_amount_paid_cannot_exceed_total(self):
        debt = DebtRecord(
            counterparty=self.counterparty,
            direction=DebtRecord.THEY_OWE_US,
            total_amount=Decimal("1000.00"),
            amount_paid=Decimal("1500.00"),
        )

        with self.assertRaises(ValidationError) as context:
            debt.full_clean()

        self.assertIn(
            "amount_paid",
            context.exception.message_dict,
        )

    def test_line_requires_product_or_description(self):
        debt = DebtRecord.objects.create(
            counterparty=self.counterparty,
            direction=DebtRecord.WE_OWE_THEM,
        )
        line = DebtLine(
            debt=debt,
            description="",
            quantity=Decimal("1.000"),
            unit="service",
            unit_price=Decimal("1000.00"),
        )

        with self.assertRaises(ValidationError) as context:
            line.full_clean()

        self.assertIn(
            "description",
            context.exception.message_dict,
        )

    def test_line_quantity_must_be_positive(self):
        debt = DebtRecord.objects.create(
            counterparty=self.counterparty,
            direction=DebtRecord.WE_OWE_THEM,
        )
        line = DebtLine(
            debt=debt,
            description="Invalid quantity",
            quantity=Decimal("0.000"),
            unit="piece",
            unit_price=Decimal("1000.00"),
        )

        with self.assertRaises(ValidationError) as context:
            line.full_clean()

        self.assertIn(
            "quantity",
            context.exception.message_dict,
        )