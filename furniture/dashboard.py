from collections import OrderedDict

from core.bi_engine import BIEngine

from furniture.models import (
    ProductionJob,
    Quotation,
    ProductionIssue,
    QualityInspection,
    ProductionTimeline,
)
from furniture.providers import FurnitureProvider


class FurnitureDashboard:
    """
    Furniture & Manufacturing Enterprise Dashboard V2.
    """

    PIPELINE_STATUSES = OrderedDict(
        [
            ("QUOTATION", "Quotation"),
            ("APPROVED", "Approved"),
            ("ORDER_CONFIRMED", "Order Confirmed"),
            ("MATERIAL_RESERVED", "Materials Reserved"),
            ("IN_PRODUCTION", "In Production"),
            ("QUALITY_CHECK", "Quality Check"),
            ("FINISHED_GOODS", "Finished Goods"),
            ("DELIVERED", "Delivered"),
        ]
    )

    @classmethod
    def get_widgets(cls):
        return [
            widget
            for widget in BIEngine.get_dashboard_widgets()
            if (
                widget.get("business_unit")
                and widget["business_unit"].code == "FURNITURE"
            )
        ]

    @classmethod
    def get_pipeline(cls):
        pipeline = []

        for status, label in cls.PIPELINE_STATUSES.items():
            queryset = ProductionJob.objects.filter(
                status=status
            ).select_related(
                "product",
                "assigned_to",
                "order",
            ).order_by("-created_at")

            pipeline.append(
                {
                    "status": status,
                    "label": label,
                    "count": queryset.count(),
                    "jobs": queryset[:6],
                }
            )

        return pipeline

    @classmethod
    def get_status_chart(cls):
        labels = []
        values = []

        for status, label in cls.PIPELINE_STATUSES.items():
            labels.append(label)
            values.append(
                ProductionJob.objects.filter(
                    status=status
                ).count()
            )

        return {
            "labels": labels,
            "values": values,
        }

    @staticmethod
    def get_quality_chart():
        return {
            "labels": ["Passed", "Failed"],
            "values": [
                QualityInspection.objects.filter(
                    passed=True
                ).count(),
                QualityInspection.objects.filter(
                    passed=False
                ).count(),
            ],
        }

    @staticmethod
    def get_workflow():
        return [
            {
                "title": "Quotation",
                "icon": "bi bi-file-earmark-text",
                "color": "warning",
                "count": FurnitureProvider.pending_quotations(),
                "url": "furniture:quotation_list",
            },
            {
                "title": "Waiting Approval",
                "icon": "bi bi-hourglass-split",
                "color": "secondary",
                "count": FurnitureProvider.jobs_waiting_approval(),
                "url": "furniture:quotation_list",
            },
            {
                "title": "Production",
                "icon": "bi bi-hammer",
                "color": "primary",
                "count": FurnitureProvider.jobs_in_production(),
                "url": "furniture:production_job_list",
            },
            {
                "title": "Quality",
                "icon": "bi bi-shield-check",
                "color": "info",
                "count": FurnitureProvider.quality_queue(),
                "url": "furniture:production_job_list",
            },
            {
                "title": "Finished",
                "icon": "bi bi-box-seam",
                "color": "success",
                "count": FurnitureProvider.finished_goods(),
                "url": "furniture:output_list",
            },
            {
                "title": "Delivered",
                "icon": "bi bi-truck",
                "color": "dark",
                "count": FurnitureProvider.delivered_jobs(),
                "url": "furniture:output_list",
            },
        ]

    @classmethod
    def get_context(cls, user=None):
        provider_summary = FurnitureProvider.summary()

        return {
            # Standard Core KPI widgets
            "widgets": cls.get_widgets(),

            # Furniture Provider KPIs
            "furniture_kpis": provider_summary,
            "alerts": FurnitureProvider.alerts(),

            # Workflow and pipeline
            "workflow": cls.get_workflow(),
            "pipeline": cls.get_pipeline(),

            # Charts
            "status_chart": cls.get_status_chart(),
            "quality_chart": cls.get_quality_chart(),

            # Operational tables
            "recent_jobs": (
                ProductionJob.objects.select_related(
                    "product",
                    "assigned_to",
                    "created_by",
                    "order",
                )
                .order_by("-created_at")[:10]
            ),

            "pending_quotations": (
                Quotation.objects.filter(
                    status="SUBMITTED"
                )
                .select_related(
                    "production_job",
                    "prepared_by",
                )
                .order_by("-created_at")[:10]
            ),

            "quality_queue": (
                ProductionJob.objects.filter(
                    status="QUALITY_CHECK"
                )
                .select_related(
                    "product",
                    "assigned_to",
                )
                .order_by("-created_at")[:10]
            ),

            "open_issues": (
                ProductionIssue.objects.filter(
                    resolved=False
                )
                .select_related(
                    "production_job"
                )
                .order_by("-created_at")[:10]
            ),

            "recent_inspections": (
                QualityInspection.objects.select_related(
                    "production_job",
                    "inspector",
                )
                .order_by("-inspected_at")[:10]
            ),

            "recent_timeline": (
                ProductionTimeline.objects.select_related(
                    "production_job",
                    "performed_by",
                )
                .order_by("-created_at")[:10]
            ),
        }