from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class MarketplaceProvider(BaseProvider):

    code = "MARKETPLACE"
    name = "Marketplace"

    @staticmethod
    def online_orders():
        try:
            from orders.models import Order
            return Order.objects.filter(order_type__iexact="ECOMMERCE").count()
        except Exception:
            return 0

    @staticmethod
    def online_products():
        try:
            from inventory.models import Product
            return Product.objects.filter(is_active=True).count()
        except Exception:
            return 0

    @classmethod
    def kpis(cls):
        return {
            "online_orders": cls.online_orders(),
            "online_products": cls.online_products(),
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
            "title": "Marketplace Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):
        return []