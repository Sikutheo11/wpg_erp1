from core.report_engine import ReportEngine
from core.providers.construction_provider import ConstructionProvider


def generate(user=None, **kwargs):

    return ReportEngine.build_report(
        title="Construction Report",
        code="CONSTRUCTION_REPORT",
        generated_by=user,
        summary=ConstructionProvider.summary(),
        rows=[],
        charts={},
    )