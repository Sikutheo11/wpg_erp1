from core.report_engine import ReportEngine
from core.providers.inventory_provider import InventoryProvider


def generate(user=None, **kwargs):

    return ReportEngine.build_report(
        title="Inventory Report",
        code="INVENTORY_REPORT",
        generated_by=user,
        summary=InventoryProvider.summary(),
        rows=[],
        charts={},
    )