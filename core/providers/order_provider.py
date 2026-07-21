from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class OrderProvider(BaseProvider):

    code = "ORDER"
    name = "Order"

    @staticmethod
    def total_orders():
        try:
            from orders.models import Order
            return Order.objects.count()
        except Exception:
            return 0

    @staticmethod
    def pending_orders():
        try:
            from orders.models import Order
            return Order.objects.filter(status__iexact="PENDING").count()
        except Exception:
            return 0

    @classmethod
    def kpis(cls):
        return {
            "total_orders": cls.total_orders(),
            "pending_orders": cls.pending_orders(),
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
            "title": "Order Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):
        alerts = []
        if cls.pending_orders() > 0:
            alerts.append("There are pending orders.")
        return alerts