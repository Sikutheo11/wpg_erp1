from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from finance.models import Account, Expense, Income, Transaction
from finance.services.account_service import AccountService
from finance.services.expense_service import ExpenseService
from finance.services.income_service import IncomeService


class FinancePostingIntegrityTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            name="Integrity Cash",
            account_type="cash",
            balance=Decimal("1000.00"),
        )

    def test_direct_model_save_does_not_post_to_ledger(self):
        Income.objects.create(
            account=self.account,
            title="Unposted import income",
            income_type="other",
            amount=Decimal("100.00"),
        )
        Expense.objects.create(
            account=self.account,
            title="Unposted import expense",
            expense_type="other",
            amount=Decimal("50.00"),
        )

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("1000.00"))
        self.assertEqual(Transaction.objects.count(), 0)

    def test_income_service_posts_once_and_links_ledger(self):
        result = IncomeService.create_income(
            account=self.account,
            title="Customer receipt",
            income_type="sales",
            amount=Decimal("250.00"),
            reference="RCPT-001",
        )

        self.account.refresh_from_db()
        income = result["income"]
        income.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("1250.00"))
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(income.ledger_transaction, result["transaction"])
        self.assertEqual(
            result["transaction"].posting_key,
            f"finance-income:{income.pk}",
        )

    def test_expense_service_rolls_back_when_funds_are_insufficient(self):
        with self.assertRaises(ValidationError):
            ExpenseService.create_expense(
                account=self.account,
                title="Too expensive",
                amount=Decimal("1500.00"),
                expense_type="other",
                reference="BILL-001",
            )

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("1000.00"))
        self.assertFalse(Expense.objects.filter(reference="BILL-001").exists())
        self.assertEqual(Transaction.objects.count(), 0)

    def test_posting_key_is_idempotent(self):
        first = AccountService.increase_balance(
            account=self.account,
            amount=Decimal("75.00"),
            description="Idempotent receipt",
            posting_key="test:receipt:1",
        )
        second = AccountService.increase_balance(
            account=self.account,
            amount=Decimal("75.00"),
            description="Idempotent receipt retry",
            posting_key="test:receipt:1",
        )

        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal("1075.00"))
        self.assertEqual(first["transaction"], second["transaction"])
        self.assertEqual(Transaction.objects.count(), 1)
