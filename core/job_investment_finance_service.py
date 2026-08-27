from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from finance.models import DebtRecord
from finance.services.debt_service import DebtService

from .job_investment_finance_models import (
    JobFinanceExpenseLink,
    JobFinanceIncomeLink,
)
from .job_investment_service import JobInvestmentService
from .job_investment_repayment_service import JobInvestorRepaymentService


class JobInvestmentFinanceService:
    ZERO = Decimal("0.00")

    @classmethod
    def money(cls, value):
        return Decimal(str(value or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    @transaction.atomic
    def link_income(cls, investment, declaration):
        link, _ = JobFinanceIncomeLink.objects.get_or_create(
            job_investment=investment,
            income_declaration=declaration,
        )
        link.save()
        cls.sync_actuals(investment)
        return link

    @classmethod
    @transaction.atomic
    def link_expense(cls, investment, expense_request):
        link, _ = JobFinanceExpenseLink.objects.get_or_create(
            job_investment=investment,
            expense_request=expense_request,
        )
        link.save()
        cls.sync_actuals(investment)
        return link

    @classmethod
    @transaction.atomic
    def sync_actuals(cls, investment):
        investment = (
            investment.__class__.objects
            .select_for_update()
            .get(pk=investment.pk)
        )

        revenue = (
            investment.finance_income_links.aggregate(
                total=Sum("amount_snapshot")
            )["total"]
            or cls.ZERO
        )
        cost = (
            investment.finance_expense_links.aggregate(
                total=Sum("amount_snapshot")
            )["total"]
            or cls.ZERO
        )

        investment.actual_revenue_snapshot = cls.money(revenue)
        investment.actual_cost_snapshot = cls.money(cost)
        investment.save(
            update_fields=[
                "actual_revenue_snapshot",
                "actual_cost_snapshot",
                "updated_at",
            ]
        )
        return investment

    @classmethod
    @transaction.atomic
    def post_settlement_to_finance(cls, agreement, actor=None):
        settlement = JobInvestmentService.prepare_investor_settlement(
            agreement
        )

        if settlement.total_due <= 0:
            raise ValidationError(
                "Settlement total must be greater than zero."
            )

        if settlement.finance_debt_record_id:
            return settlement

        investment = agreement.job_investment

        debt = DebtService.create_debt(
            counterparty=agreement.investor,
            direction=DebtRecord.WE_OWE_THEM,
            business_unit=investment.order.business_unit,
            due_date=agreement.repayment_due_date,
            notes=(
                f"Investor settlement for {investment.reference}; "
                f"agreement {agreement.agreement_number}."
            ),
            actor=actor,
            lines=[
                {
                    "item_type": "OTHER",
                    "description": (
                        f"Investor capital and return - "
                        f"{agreement.agreement_number}"
                    ),
                    "quantity": Decimal("1.000"),
                    "unit": "settlement",
                    "unit_price": settlement.total_due,
                }
            ],
        )

        settlement.finance_debt_record = debt
        settlement.status = "APPROVED"
        settlement.save(
            update_fields=[
                "finance_debt_record",
                "status",
                "updated_at",
            ]
        )
        JobInvestorRepaymentService.refresh_investment_status(
            investment
        )
        return settlement
