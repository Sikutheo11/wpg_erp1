from core.report_registry import ReportRegistry

from . import executive
from . import finance
from . import inventory
from . import furniture
from . import construction
from . import agriculture
from . import marketplace


def register_reports():
    ReportRegistry.register(
        code="EXECUTIVE",
        name="Executive Report",
        provider=executive.generate,
    )

    ReportRegistry.register(
        code="FINANCE",
        name="Finance Report",
        provider=finance.generate,
    )

    ReportRegistry.register(
        code="INVENTORY",
        name="Inventory Report",
        provider=inventory.generate,
    )

    ReportRegistry.register(
        code="FURNITURE",
        name="Furniture & Manufacturing Report",
        provider=furniture.generate,
    )

    ReportRegistry.register(
        code="CONSTRUCTION",
        name="Construction Report",
        provider=construction.generate,
    )

    ReportRegistry.register(
        code="AGRICULTURE",
        name="Agriculture & Poultry Report",
        provider=agriculture.generate,
    )

    ReportRegistry.register(
        code="MARKETPLACE",
        name="Marketplace Report",
        provider=marketplace.generate,
    )


register_reports()