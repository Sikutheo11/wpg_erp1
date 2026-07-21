from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce

from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class ConstructionProvider(BaseProvider):

    code = "CONSTRUCTION"
    name = "Construction & Built Environment"

    @staticmethod
    def active_projects():
        try:
            from Construction.models import Project
            return Project.objects.exclude(status__iexact="COMPLETED").count()
        except Exception:
            return 0

    @staticmethod
    def delayed_projects():
        try:
            from Construction.models import Project
            return Project.objects.filter(status__iexact="DELAYED").count()
        except Exception:
            return 0

    @staticmethod
    def budget_used():
        try:
            from Construction.models import Expense
            return Expense.objects.aggregate(
                total=Coalesce(Sum("amount"), Decimal("0.00"))
            )["total"]
        except Exception:
            return Decimal("0.00")

    @classmethod
    def kpis(cls):
        return {
            "active_projects": cls.active_projects(),
            "delayed_projects": cls.delayed_projects(),
            "budget_used": cls.budget_used(),
        }

    @classmethod
    def summary(cls):
        return cls.kpis()

    @classmethod
    def dashboard(cls):
        return {"cards": cls.kpis(), "alerts": cls.alerts()}

    @classmethod
    def report(cls, user=None, **kwargs):
        return {
            "title": "Construction Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):
        alerts = []
        if cls.delayed_projects() > 0:
            alerts.append("There are delayed construction projects.")
        return alerts