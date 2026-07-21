from core.report_engine import ReportEngine
from core.providers.agriculture_provider import AgricultureProvider


def generate(user=None, **kwargs):

    return ReportEngine.build_report(
        title="Agriculture & Poultry Report",
        code="AGRICULTURE_REPORT",
        generated_by=user,
        summary=AgricultureProvider.summary(),
        rows=[],
        charts={},
    )