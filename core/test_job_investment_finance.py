from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.job_investment_finance_models import (
    JobFinanceExpenseLink,
    JobFinanceIncomeLink,
)
from core.job_investment_finance_service import JobInvestmentFinanceService
from core.job_investment_models import (
    JobInvestment,
    JobInvestorAgreement,
    JobInvestorContribution,
)
from finance.models import (
    Counterparty,
    ExpenseRequest,
    IncomeDeclaration,
)
from orders.models import Order


class JobInvestmentFinanceIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="finance-job-admin",
            password="StrongPass123!",
            email="finance-job@example.com",
            first_name="Finance",
            last_name="Job Admin",
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
            status="FUNDING",
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
            return_model="PROFIT_SHARE",
            profit_share_percent=Decimal("25.00"),
            status="ACTIVE",
        )

    def test_received_contribution_requires_finance_confirmation(self):
        declaration = IncomeDeclaration.objects.create(
            recorded_by=self.user,
            business_unit="FURNITURE",
            title="Investor funding",
            source_type="INVESTMENT",
            amount=Decimal("30000000.00"),
            received_from=self.investor,
            receipt_method="bank",
            receipt_date="2026-08-27",
            reference="INV-1",
            status="UNIT_APPROVED",
        )

        contribution = JobInvestorContribution(
            agreement=self.agreement,
            amount=Decimal("30000000.00"),
            status="RECEIVED",
            received_date="2026-08-27",
            finance_income_declaration=declaration,
        )

        with self.assertRaises(ValidationError):
            contribution.full_clean()

    def test_finance_links_drive_actual_profit(self):
        revenue = IncomeDeclaration.objects.create(
            recorded_by=self.user,
            business_unit="FURNITURE",
            title="Customer receipt",
            source_type="SERVICE",
            amount=Decimal("100000000.00"),
            receipt_method="bank",
            receipt_date="2026-08-27",
            reference="REV-1",
            status="FINANCE_CONFIRMED",
        )

        expense = ExpenseRequest.objects.create(
            requested_by=self.user,
            business_unit="FURNITURE",
            request_type="DIRECT_PAYMENT",
            title="Project materials",
            expense_type="raw_material",
            purpose="School desks",
            payee=self.investor,
            amount_requested=Decimal("80000000.00"),
            needed_by="2026-08-27",
            status="PAID",
            amount_paid=Decimal("80000000.00"),
        )

        JobFinanceIncomeLink.objects.create(
            job_investment=self.investment,
            income_declaration=revenue,
        )
        JobFinanceExpenseLink.objects.create(
            job_investment=self.investment,
            expense_request=expense,
        )

        JobInvestmentFinanceService.sync_actuals(self.investment)
        self.investment.refresh_from_db()

        self.assertEqual(
            self.investment.actual_revenue_snapshot,
            Decimal("100000000.00"),
        )
        self.assertEqual(
            self.investment.actual_cost_snapshot,
            Decimal("80000000.00"),
        )
        self.assertEqual(
            self.investment.actual_profit_snapshot,
            Decimal("20000000.00"),
        )
