from decimal import Decimal

from django.test import TestCase

from core.job_investment_models import (
    JobInvestment,
    JobInvestorAgreement,
    JobInvestorContribution,
    JobInvestorSettlement,
)
from finance.models import Counterparty
from orders.models import Order


class SingleJobInvestmentTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            business_unit="FURNITURE",
            order_type="CUSTOM_FURNITURE",
            status="READY_FOR_PRODUCTION",
            customer_name="Karongi School",
            customer_phone="0788000000",
            subtotal=Decimal("100000000.00"),
            total_amount=Decimal("100000000.00"),
        )

        self.investment = JobInvestment.objects.create(
            order=self.order,
            estimated_job_cost=Decimal("80000000.00"),
            contract_value=Decimal("100000000.00"),
            wpg_capital_committed=Decimal("50000000.00"),
            status="FUNDING",
        )

        self.investor = Counterparty.objects.create(
            party_type="INDIVIDUAL",
            name="Single Job Investor",
            phone="0788123456",
        )

        self.agreement = JobInvestorAgreement.objects.create(
            job_investment=self.investment,
            investor=self.investor,
            committed_capital=Decimal("30000000.00"),
            return_model="PROFIT_SHARE",
            profit_share_percent=Decimal("25.00"),
            status="ACTIVE",
        )

    def test_funding_gap_uses_only_received_investor_money(self):
        self.assertEqual(
            self.investment.funding_gap,
            Decimal("30000000.00"),
        )

        JobInvestorContribution.objects.create(
            agreement=self.agreement,
            amount=Decimal("30000000.00"),
            status="RECEIVED",
            received_date="2026-08-27",
        )

        self.assertEqual(
            self.investment.investor_capital_received,
            Decimal("30000000.00"),
        )
        self.assertEqual(
            self.investment.total_capital_available,
            Decimal("80000000.00"),
        )
        self.assertEqual(
            self.investment.funding_gap,
            Decimal("0.00"),
        )

    def test_contributions_cannot_exceed_agreed_capital(self):
        JobInvestorContribution.objects.create(
            agreement=self.agreement,
            amount=Decimal("25000000.00"),
            status="RECEIVED",
            received_date="2026-08-27",
        )

        with self.assertRaises(Exception):
            JobInvestorContribution.objects.create(
                agreement=self.agreement,
                amount=Decimal("6000000.00"),
                status="RECEIVED",
                received_date="2026-08-28",
            )

    def test_profit_share_uses_positive_actual_job_profit(self):
        self.assertEqual(
            self.agreement.calculate_investor_profit(
                actual_job_profit=Decimal("20000000.00")
            ),
            Decimal("5000000.00"),
        )

        self.assertEqual(
            self.agreement.calculate_investor_profit(
                actual_job_profit=Decimal("-1000000.00")
            ),
            Decimal("0.00"),
        )

    def test_settlement_is_principal_plus_investor_profit(self):
        settlement = JobInvestorSettlement.objects.create(
            agreement=self.agreement,
            principal_due=Decimal("30000000.00"),
            investor_profit_due=Decimal("5000000.00"),
            amount_paid=Decimal("10000000.00"),
        )

        self.assertEqual(
            settlement.total_due,
            Decimal("35000000.00"),
        )
        self.assertEqual(
            settlement.balance_due,
            Decimal("25000000.00"),
        )
        self.assertEqual(
            settlement.status,
            "PARTIAL",
        )
