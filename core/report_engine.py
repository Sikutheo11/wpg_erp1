# ==========================================
# WPG BOS
# Reporting Engine
# ==========================================

from django.utils import timezone

from .report_registry import ReportRegistry


class ReportEngine:
    """
    WPG BOS Reporting Engine.

    The engine is now a central orchestrator.
    Actual reports are registered through ReportRegistry.
    """

    @staticmethod
    def build_report(
        title,
        code,
        generated_by=None,
        filters=None,
        summary=None,
        rows=None,
        charts=None,
    ):
        return {
            "title": title,
            "code": code,
            "generated_at": timezone.now(),
            "generated_by": generated_by,
            "filters": filters or {},
            "summary": summary or {},
            "rows": rows or [],
            "charts": charts or {},
        }

    @staticmethod
    def generate(code, user=None, **kwargs):
        return ReportRegistry.generate(
            code=code,
            user=user,
            **kwargs
        )

    @staticmethod
    def all_reports():
        return ReportRegistry.all()