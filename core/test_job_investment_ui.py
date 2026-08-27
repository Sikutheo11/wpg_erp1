from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from finance.models import Counterparty
from furniture.planner_models import ProductionPlan
from orders.models import Order

from core.job_investment_models import JobInvestment, JobInvestorAgreement
from core.job_investment_service import JobInvestmentService


class JobInvestmentUITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="job-investment-admin",
            password="StrongPass123!",
            email="admin@example.com",
            first_name="Job",
            last_name="Admin",
        )
        self.client.force_login(self.user)

        self.order = Order.objects.create(
            business_unit="FURNITURE",
            order_type="CUSTOM_FURNITURE",
            status="READY_FOR_PRODUCTION",
            customer_name="Karongi School",
            customer_phone="0788000000",
            subtotal=Decimal("100000000.00"),
        )
        ProductionPlan.objects.create(
            order=self.order,
            name="School Desks",
            quantity=Decimal("2000.00"),
            status="CALCULATED",
            estimated_total_cost=Decimal("80000000.00"),
            estimated_cost_per_unit=Decimal("40000.00"),
            recommended_selling_price=Decimal("100000000.00"),
            expected_profit=Decimal("20000000.00"),
        )

    def test_open_job_funding_from_order(self):
        response = self.client.post(
            reverse("core:job_investment_open", args=[self.order.pk]),
            {
                "wpg_capital_committed": "50000000.00",
                "notes": "External funding needed.",
            },
        )
        self.assertEqual(response.status_code, 302)
        investment = JobInvestment.objects.get(order=self.order)
        self.assertEqual(investment.estimated_job_cost, Decimal("80000000.00"))
        self.assertEqual(investment.wpg_capital_committed, Decimal("50000000.00"))
        self.assertEqual(investment.funding_gap, Decimal("30000000.00"))

    def test_investment_detail_page_loads(self):
        investment = JobInvestmentService.create_or_refresh_from_order(
            self.order,
            wpg_capital_committed=Decimal("50000000.00"),
            actor=self.user,
        )
        response = self.client.get(
            reverse("core:job_investment_detail", args=[investment.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Funding Gap")
        self.assertContains(response, "Investor Agreements")

    def test_add_and_activate_investor_agreement(self):
        investment = JobInvestmentService.create_or_refresh_from_order(
            self.order,
            wpg_capital_committed=Decimal("50000000.00"),
            actor=self.user,
        )
        investor = Counterparty.objects.create(
            party_type="INDIVIDUAL",
            name="Investor One",
            phone="0788123456",
        )
        response = self.client.post(
            reverse("core:job_investment_add_agreement", args=[investment.pk]),
            {
                "investor": investor.pk,
                "committed_capital": "30000000.00",
                "return_model": "PROFIT_SHARE",
                "fixed_profit_amount": "0",
                "profit_share_percent": "25",
                "agreement_date": "2026-08-27",
                "repayment_due_date": "",
                "terms": "Capital plus 25% of positive actual profit.",
            },
        )
        self.assertEqual(response.status_code, 302)
        agreement = JobInvestorAgreement.objects.get(
            job_investment=investment,
            investor=investor,
        )
        self.assertEqual(agreement.status, "DRAFT")

        response = self.client.post(
            reverse("core:job_investment_approve_agreement", args=[agreement.pk])
        )
        self.assertEqual(response.status_code, 302)
        agreement.refresh_from_db()
        self.assertEqual(agreement.status, "ACTIVE")
