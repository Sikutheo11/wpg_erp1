from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from core.job_investment_models import (
    JobInvestment,
    JobInvestorSettlement,
)


class JobInvestmentService:
    """
    Orchestrates job funding without replacing shared engines.

    Source ownership:
      Orders -> job/contract
      Furniture ProductionPlan -> estimated furniture cost
      SalesQuotation -> customer contract/quotation value
      Finance -> actual cash, expenses, revenue, debt and repayment
    """

    ZERO = Decimal("0.00")

    @classmethod
    def money(cls, value):
        return Decimal(str(value or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    @transaction.atomic
    def create_or_refresh_from_order(
        cls,
        order,
        *,
        wpg_capital_committed=None,
        actor=None,
    ):
        investment = getattr(order, "job_investment", None)

        if investment is None:
            investment = JobInvestment(
                order=order,
                opened_by=actor,
            )

        quotation = getattr(order, "customer_quotation", None)
        investment.contract_value = cls.money(
            quotation.total_amount
            if quotation is not None
            else order.total_amount
        )

        if order.business_unit == "FURNITURE":
            plans = order.furniture_production_plans.all()

            if not plans.exists():
                raise ValidationError(
                    "Create at least one Furniture Production Plan first."
                )

            if plans.exclude(
                status__in=["CALCULATED", "APPROVED"]
            ).exists():
                raise ValidationError(
                    "Calculate all Furniture Production Plans first."
                )

            investment.estimated_job_cost = sum(
                (
                    cls.money(plan.estimated_total_cost)
                    for plan in plans
                ),
                cls.ZERO,
            )
        elif investment.estimated_job_cost <= 0:
            raise ValidationError(
                "Enter the approved estimated job cost before opening funding."
            )

        if wpg_capital_committed is not None:
            wpg_capital_committed = cls.money(
                wpg_capital_committed
            )
            if wpg_capital_committed < 0:
                raise ValidationError(
                    "WPG committed capital cannot be negative."
                )
            investment.wpg_capital_committed = (
                wpg_capital_committed
            )

        investment.status = (
            "FUNDED"
            if investment.funding_gap <= 0
            else "FUNDING"
        )
        investment.save()
        return investment

    @classmethod
    @transaction.atomic
    def prepare_investor_settlement(
        cls,
        agreement,
        *,
        actual_job_profit=None,
    ):
        if agreement.status not in {
            "APPROVED",
            "ACTIVE",
            "SETTLEMENT_DUE",
        }:
            raise ValidationError(
                "Only an approved or active agreement can be settled."
            )

        principal = cls.money(agreement.capital_received)

        investor_profit = agreement.calculate_investor_profit(
            actual_job_profit=actual_job_profit
        )

        settlement, _ = (
            JobInvestorSettlement.objects.get_or_create(
                agreement=agreement
            )
        )
        settlement.principal_due = principal
        settlement.investor_profit_due = investor_profit
        settlement.save()

        agreement.status = "SETTLEMENT_DUE"
        agreement.save(
            update_fields=["status", "updated_at"]
        )

        investment = agreement.job_investment
        if investment.status not in {"CLOSED", "CANCELLED"}:
            investment.status = "SETTLEMENT"
            investment.save(
                update_fields=["status", "updated_at"]
            )

        return settlement
