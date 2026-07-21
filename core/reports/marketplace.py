from core.report_engine import ReportEngine
from core.providers.marketplace_provider import MarketplaceProvider


def generate(user=None, **kwargs):

    return ReportEngine.build_report(
        title="Marketplace Report",
        code="MARKETPLACE_REPORT",
        generated_by=user,
        summary=MarketplaceProvider.summary(),
        rows=[],
        charts={},
    )