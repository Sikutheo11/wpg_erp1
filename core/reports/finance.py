from core.report_engine import ReportEngine
from core.providers.finance_provider import FinanceProvider


def generate(user=None, **kwargs):

    return ReportEngine.build_report(
        title="Finance Report",
        code="FINANCE_REPORT",
        generated_by=user,
        summary=FinanceProvider.summary(),
        rows=[],
        charts={},
    )