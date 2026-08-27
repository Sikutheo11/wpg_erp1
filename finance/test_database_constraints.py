from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from finance.models import (
    Account,
    Expense,
    ExpenseRequest,
    Income,
    IncomeDeclaration,
    Payable,
    Receivable,
    Transaction,
)


class FinanceDatabaseConstraintTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            name="Constraint Cash",
            account_type="cash",
            balance=Decimal("100.00"),
        )

    def test_transaction_amount_must_be_positive_at_database_level(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Transaction.objects.create(
                account=self.account,
                transaction_type="income",
                amount=Decimal("0.00"),
                description="Invalid zero transaction",
            )

    def test_income_amount_must_be_positive_at_database_level(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Income.objects.create(
                account=self.account,
                title="Invalid income",
                income_type="other",
                amount=Decimal("-1.00"),
            )

    def test_required_finance_constraints_are_declared(self):
        expected = {
            "finance_tx_amount_gt_zero",
            "finance_income_amount_gt_zero",
            "finance_income_decl_amount_gt_zero",
            "finance_expense_amount_gt_zero",
            "finance_exp_req_requested_gt_zero",
            "finance_exp_req_paid_nonnegative",
            "finance_recv_total_gt_zero",
            "finance_recv_paid_nonnegative",
            "finance_recv_paid_lte_total",
            "finance_pay_total_gt_zero",
            "finance_pay_paid_nonnegative",
            "finance_pay_paid_lte_total",
        }
        actual = {
            constraint.name
            for model in (
                Transaction,
                Income,
                IncomeDeclaration,
                Expense,
                ExpenseRequest,
                Receivable,
                Payable,
            )
            for constraint in model._meta.constraints
        }
        self.assertTrue(expected.issubset(actual))
