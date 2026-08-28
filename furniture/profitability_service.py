from decimal import Decimal


class FurnitureProfitabilityReconciliationService:
    """
    Read-only final reconciliation for a Furniture ProductionJob.

    Order owns the customer commercial amount/payment status.
    JobInvestment/Finance owns linked finance actuals when present.
    Furniture owns manufacturing cost.

    Investor capital is funding and must never be treated as revenue.
    """

    ZERO = Decimal("0.00")
    HUNDRED = Decimal("100.00")

    @classmethod
    def money(cls, value):
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))

    @classmethod
    def build(cls, job, evidence=None):
        order = getattr(job, "order", None)

        if evidence is None:
            from .lifecycle_evidence import ProductionJobLifecycleEvidence
            evidence = ProductionJobLifecycleEvidence.build(job)

        payment_complete = bool(
            evidence.get("finance", {}).get("payment_complete", False)
        )
        delivery_complete = bool(
            evidence.get("delivery", {}).get("complete", False)
        )
        all_output_released = bool(
            evidence.get("inventory", {}).get("all_output_released", False)
        )

        investment = None
        if order is not None:
            try:
                investment = order.job_investment
            except Exception:
                investment = None

        finance_revenue = cls.ZERO
        finance_cost = cls.ZERO
        income_links = 0
        expense_links = 0

        if investment is not None:
            finance_revenue = cls.money(
                getattr(investment, "actual_revenue_snapshot", cls.ZERO)
            )
            finance_cost = cls.money(
                getattr(investment, "actual_cost_snapshot", cls.ZERO)
            )
            try:
                income_links = investment.finance_income_links.count()
                expense_links = investment.finance_expense_links.count()
            except Exception:
                pass

        order_revenue = cls.money(
            getattr(order, "total_amount", cls.ZERO)
            if payment_complete and order is not None
            else cls.ZERO
        )

        actual_revenue = (
            finance_revenue
            if finance_revenue > cls.ZERO
            else order_revenue
        )
        revenue_source = (
            "FINANCE_LINKS"
            if finance_revenue > cls.ZERO
            else (
                "PAID_ORDER"
                if order_revenue > cls.ZERO
                else "UNRECONCILED"
            )
        )

        production_cost = cls.ZERO
        if getattr(job, "pk", None):
            # IMPORTANT: lazy import intentionally prevents Django startup cycle:
            # lifecycle_guards -> profitability_service -> services package
            # -> production_service -> lifecycle_guards
            from .services.costing_service import ProductionCostService

            production_cost = cls.money(
                ProductionCostService.total_cost(job)
            )

        # Do not add these together. Finance cost may already represent
        # manufacturing expenses that Furniture also measured operationally.
        actual_cost = (
            finance_cost
            if finance_cost > cls.ZERO
            else production_cost
        )
        cost_source = (
            "FINANCE_LINKS"
            if finance_cost > cls.ZERO
            else (
                "PRODUCTION_COST"
                if production_cost > cls.ZERO
                else "NONE"
            )
        )

        actual_profit = cls.money(actual_revenue - actual_cost)

        profit_margin = cls.ZERO
        if actual_revenue > cls.ZERO:
            profit_margin = cls.money(
                (actual_profit / actual_revenue) * cls.HUNDRED
            )

        investment_status = evidence.get("finance", {}).get(
            "investment_status"
        )
        investment_settled = investment_status in (
            None,
            "",
            "CLOSED",
            "CANCELLED",
        )

        order_total = cls.money(
            getattr(order, "total_amount", cls.ZERO)
            if order is not None
            else cls.ZERO
        )
        revenue_reconciled = (
            payment_complete or order_total == cls.ZERO
        )

        reconciliation_ready = bool(
            delivery_complete
            and all_output_released
            and revenue_reconciled
            and investment_settled
        )

        return {
            "actual_revenue": actual_revenue,
            "actual_cost": actual_cost,
            "production_cost": production_cost,
            "finance_cost": finance_cost,
            "actual_profit": actual_profit,
            "profit_margin": profit_margin,
            "revenue_source": revenue_source,
            "cost_source": cost_source,
            "income_link_count": income_links,
            "expense_link_count": expense_links,
            "payment_complete": payment_complete,
            "delivery_complete": delivery_complete,
            "all_output_released": all_output_released,
            "investment_status": investment_status,
            "investment_settled": investment_settled,
            "reconciliation_ready": reconciliation_ready,
        }
