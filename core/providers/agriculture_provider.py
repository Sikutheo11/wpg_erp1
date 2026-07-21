from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class AgricultureProvider(BaseProvider):

    code = "AGRICULTURE"
    name = "Agriculture & Poultry"

    @staticmethod
    def egg_production():
        return 0

    @staticmethod
    def mortality():
        return 0

    @staticmethod
    def poultry_batches():
        return 0

    @staticmethod
    def feed_consumption():
        return 0

    @classmethod
    def kpis(cls):
        return {
            "egg_production": cls.egg_production(),
            "mortality": cls.mortality(),
            "poultry_batches": cls.poultry_batches(),
            "feed_consumption": cls.feed_consumption(),
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
            "title": "Agriculture & Poultry Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):
        return []