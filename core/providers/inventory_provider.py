from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class InventoryProvider(BaseProvider):

    code = "INVENTORY"
    name = "Inventory"

    @staticmethod
    def products():
        try:
            from inventory.models import Product
            return Product.objects.count()
        except Exception:
            return 0

    @staticmethod
    def raw_materials():
        try:
            from inventory.models import RawMaterial
            return RawMaterial.objects.count()
        except Exception:
            return 0

    @staticmethod
    def stock_alerts():
        try:
            from inventory.models import RawMaterial
            return RawMaterial.objects.filter(minimum_stock__gte=0).count()
        except Exception:
            return 0

    @classmethod
    def kpis(cls):
        return {
            "products": cls.products(),
            "raw_materials": cls.raw_materials(),
            "stock_alerts": cls.stock_alerts(),
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
            "title": "Inventory Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):
        alerts = []
        if cls.stock_alerts() > 0:
            alerts.append("Some stock items require attention.")
        return alerts