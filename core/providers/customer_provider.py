from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class CustomerProvider(BaseProvider):

    code = "CUSTOMER"
    name = "Customer"

    @staticmethod
    def total_customers():
        try:
            from sales.models import Customer
            return Customer.objects.count()
        except Exception:
            return 0

    @classmethod
    def kpis(cls):
        return {
            "total_customers": cls.total_customers(),
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
            "title": "Customer Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):
        return []