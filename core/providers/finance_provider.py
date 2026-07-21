"""
==========================================
WPG BOS
Finance Provider
==========================================
"""

from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class FinanceProvider(BaseProvider):

    code = "FINANCE"
    name = "Finance"

    # =====================================================
    # KPI METHODS
    # =====================================================

    @staticmethod
    def total_income():
        try:
            from finance.models import Income

            return Income.objects.aggregate(
                total=Coalesce(
                    Sum("amount"),
                    Decimal("0.00")
                )
            )["total"]

        except Exception:
            return Decimal("0.00")

    @staticmethod
    def total_expense():
        try:
            from finance.models import Expense

            return Expense.objects.aggregate(
                total=Coalesce(
                    Sum("amount"),
                    Decimal("0.00")
                )
            )["total"]

        except Exception:
            return Decimal("0.00")

    @classmethod
    def net_profit(cls):
        return (
            cls.total_income()
            - cls.total_expense()
        )

    # =====================================================
    # PROVIDER API
    # =====================================================

    @classmethod
    def kpis(cls):

        return {
            "total_income": cls.total_income(),
            "total_expense": cls.total_expense(),
            "net_profit": cls.net_profit(),
        }

    @classmethod
    def summary(cls):
        return cls.kpis()

    @classmethod
    def dashboard(cls):

        return {
            "cards": cls.kpis(),
            "alerts": cls.alerts(),
        }

    @classmethod
    def report(cls, user=None, **kwargs):

        return {
            "title": "Finance Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):

        alerts = []

        if cls.net_profit() < 0:
            alerts.append(
                "Business is operating at a loss."
            )

        return alerts