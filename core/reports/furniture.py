from core.report_engine import ReportEngine
from core.providers.furniture_provider import FurnitureProvider


def generate(user=None, **kwargs):

    return ReportEngine.build_report(
        title="Furniture & Manufacturing Report",
        code="FURNITURE_REPORT",
        generated_by=user,
        summary=FurnitureProvider.summary(),
        rows=[],
        charts={},
    )