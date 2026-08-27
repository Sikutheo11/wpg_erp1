from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.job_investment_models import (
    JobInvestment,
    JobInvestorAgreement,
    JobInvestorSettlement,
)
from core.job_investment_repayment_service import JobInvestorRepaymentService
from finance.models import Counterparty, DebtRecord
from orders.models import Order


class JobInvestorRepaymentTrackingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="settlement-admin",
            password="StrongPass123!",
            email="settlement@example.com",
            first_name="Settlement",
            last_name="Admin",
        )

        self.order = Order.objects.create(
            business_unit="FURNITURE",
            order_type="CUSTOM_FURNITURE",
            status="READY_FOR_PRODUCTION",
            customer_name="School",
            customer_phone="0788000000",
            subtotal=Decimal("100000000.00"),
        )

        self.investment = JobInvestment.objects.create(
            order=self.order,
            estimated_job_cost=Decimal("80000000.00"),
            contract_value=Decimal("100000000.00"),
            wpg_capital_committed=Decimal("50000000.00"),
            status="SETTLEMENT",
        )

        self.investor = Counterparty.objects.create(
            party_type="INDIVIDUAL",
            name="Investor",
            phone="0788123456",
        )

        self.agreement = JobInvestorAgreement.objects.create(
            job_investment=self.investment,
            investor=self.investor,
            committed_capital=Decimal("30000000.00"),
            return_model="FIXED_PROFIT",
            fixed_profit_amount=Decimal("5000000.00"),
            status="SETTLEMENT_DUE",
        )

        self.debt = DebtRecord.objects.create(
            counterparty=self.investor,
            direction=DebtRecord.WE_OWE_THEM,
            business_unit="FURNITURE",
            total_amount=Decimal("35000000.00"),
            amount_paid=Decimal("0.00"),
            status=DebtRecord.OPEN,
            created_by=self.user,
        )

        self.settlement = JobInvestorSettlement.objects.create(
            agreement=self.agreement,
            principal_due=Decimal("30000000.00"),
            investor_profit_due=Decimal("5000000.00"),
            amount_paid=Decimal("0.00"),
            status="APPROVED",
            finance_debt_record=self.debt,
        )

    def test_partial_finance_payment_updates_settlement(self):
        self.debt.amount_paid = Decimal("10000000.00")
        self.debt.status = DebtRecord.PARTIAL
        self.debt.save(update_fields=["amount_paid", "status", "updated_at"])

        JobInvestorRepaymentService.sync_settlement_from_finance(self.settlement)

        self.settlement.refresh_from_db()
        self.agreement.refresh_from_db()
        self.investment.refresh_from_db()

        self.assertEqual(self.settlement.amount_paid, Decimal("10000000.00"))
        self.assertEqual(self.settlement.status, "PARTIAL")
        self.assertEqual(self.agreement.status, "SETTLEMENT_DUE")
        self.assertEqual(self.investment.status, "SETTLEMENT")

    def test_full_finance_payment_closes_agreement_and_job(self):
        self.debt.amount_paid = Decimal("35000000.00")
        self.debt.status = DebtRecord.PAID
        self.debt.save(update_fields=["amount_paid", "status", "updated_at"])

        JobInvestorRepaymentService.sync_settlement_from_finance(self.settlement)

        self.settlement.refresh_from_db()
        self.agreement.refresh_from_db()
        self.investment.refresh_from_db()

        self.assertEqual(self.settlement.amount_paid, Decimal("35000000.00"))
        self.assertEqual(self.settlement.status, "SETTLED")
        self.assertEqual(self.agreement.status, "SETTLED")
        self.assertEqual(self.investment.status, "CLOSED")
        self.assertIsNotNone(self.investment.closed_at)
