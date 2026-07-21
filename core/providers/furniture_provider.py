from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce

from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class FurnitureProvider(BaseProvider):

    code = "FURNITURE"
    name = "Furniture & Manufacturing"

    @staticmethod
    def active_jobs():
        try:
            from furniture.models import ProductionJob
            return ProductionJob.objects.exclude(status__iexact="COMPLETED").count()
        except Exception:
            return 0

    @staticmethod
    def completed_outputs():
        try:
            from furniture.models import ProductionOutput
            return ProductionOutput.objects.count()
        except Exception:
            return 0

    @staticmethod
    def material_usage():
        try:
            from furniture.models import ProductionMaterial
            return ProductionMaterial.objects.aggregate(
                total=Coalesce(Sum("total_cost"), Decimal("0.00"))
            )["total"]
        except Exception:
            return Decimal("0.00")

    @classmethod
    def kpis(cls):
        return {
            "active_jobs": cls.active_jobs(),
            "completed_outputs": cls.completed_outputs(),
            "material_usage": cls.material_usage(),
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
            "title": "Furniture & Manufacturing Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):
        alerts = []
        if cls.active_jobs() > 0:
            alerts.append("There are active production jobs.")
        return alerts