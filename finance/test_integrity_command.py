from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from finance.models import Account, Income, Transaction
from finance.services.income_service import IncomeService


class FinanceIntegrityCommandTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            name="Audit Cash",
            account_type="cash",
            balance=Decimal("500.00"),
        )

    def test_clean_posting_passes_strict_audit(self):
        IncomeService.create_income(
            account=self.account,
            title="Audited receipt",
            amount=Decimal("100.00"),
            income_type="other",
            reference="AUDIT-001",
        )
        output = StringIO()

        call_command(
            "audit_finance_integrity",
            "--fail-on-errors",
            stdout=output,
        )

        self.assertIn("errors=0 warnings=0", output.getvalue())

    def test_legacy_unlinked_record_is_reported_as_warning(self):
        Income.objects.create(
            account=self.account,
            title="Legacy import",
            amount=Decimal("25.00"),
            income_type="other",
        )
        output = StringIO()

        call_command(
            "audit_finance_integrity",
            "--fail-on-errors",
            stdout=output,
        )

        self.assertIn("errors=0 warnings=1", output.getvalue())
        self.assertIn("Income record(s) have no linked ledger", output.getvalue())

    def test_mismatched_ledger_fails_strict_audit(self):
        ledger = Transaction.objects.create(
            account=self.account,
            transaction_type="income",
            amount=Decimal("10.00"),
            description="Incorrect posting",
            posting_key="finance-income:1",
        )
        Income.objects.create(
            account=self.account,
            title="Mismatched income",
            amount=Decimal("20.00"),
            income_type="other",
            ledger_transaction=ledger,
        )

        with self.assertRaises(CommandError):
            call_command(
                "audit_finance_integrity",
                "--fail-on-errors",
                stdout=StringIO(),
                stderr=StringIO(),
            )
