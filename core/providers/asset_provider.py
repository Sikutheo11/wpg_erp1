from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class AssetProvider(BaseProvider):

    code = "ASSET"
    name = "Asset"

    @staticmethod
    def total_assets():
        try:
            from inventory.models import Asset
            return Asset.objects.count()
        except Exception:
            return 0

    @staticmethod
    def active_assets():
        try:
            from inventory.models import Asset
            return Asset.objects.filter(status__iexact="ACTIVE").count()
        except Exception:
            return 0

    @classmethod
    def kpis(cls):
        return {
            "total_assets": cls.total_assets(),
            "active_assets": cls.active_assets(),
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
            "title": "Asset Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):
        return []