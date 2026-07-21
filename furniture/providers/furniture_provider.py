from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from core.providers.base import BaseProvider
from core.providers.registry import ProviderRegistry

from furniture.models import (
    ProductionJob,
    ProductionOutput,
    ProductionMaterial,
    ProductionIssue,
    QualityInspection,
    Quotation,
)


@ProviderRegistry.register
class FurnitureProvider(BaseProvider):

    code = "FURNITURE"
    name = "Furniture & Manufacturing"

    # =====================================================
    # PRODUCTION
    # =====================================================

    @staticmethod
    def active_jobs():
        return ProductionJob.objects.exclude(
            status__in=[
                "COMPLETED",
                "DELIVERED",
                "CANCELLED",
            ]
        ).count()

    @staticmethod
    def completed_jobs():
        return ProductionJob.objects.filter(
            status="COMPLETED"
        ).count()

    @staticmethod
    def delayed_jobs():
        return ProductionJob.objects.filter(
            status="DELAYED"
        ).count()

    @staticmethod
    def jobs_in_production():
        return ProductionJob.objects.filter(
            status="IN_PRODUCTION"
        ).count()

    @staticmethod
    def jobs_waiting_approval():
        return ProductionJob.objects.filter(
            status="QUOTATION_PENDING"
        ).count()

    @staticmethod
    def jobs_in_quality():
        return ProductionJob.objects.filter(
            status="QUALITY_CHECK"
        ).count()

    @staticmethod
    def finished_goods():
        return ProductionJob.objects.filter(
            status="FINISHED_GOODS"
        ).count()
    
    @staticmethod
    def delivered_jobs():
        return ProductionJob.objects.filter(
            status="DELIVERED"
        ).count()

    # =====================================================
    # OUTPUTS
    # =====================================================

    @staticmethod
    def completed_outputs():
        return ProductionOutput.objects.count()

    # =====================================================
    # QUOTATIONS
    # =====================================================

    @staticmethod
    def pending_quotations():
        return Quotation.objects.filter(
            status="submitted"
        ).count()

    @staticmethod
    def approved_quotations():
        return Quotation.objects.filter(
            status="approved"
        ).count()

    # =====================================================
    # QUALITY
    # =====================================================

    @staticmethod
    def quality_queue():
        return ProductionJob.objects.filter(
            status="QUALITY_CHECK"
        ).count()

    @staticmethod
    def quality_passed():
        return QualityInspection.objects.filter(
            passed=True
        ).count()

    @staticmethod
    def quality_failed():
        return QualityInspection.objects.filter(
            passed=False
        ).count()

    # =====================================================
    # ISSUES
    # =====================================================

    @staticmethod
    def open_issues():
        return ProductionIssue.objects.filter(
            resolved=False
        ).count()

    # =====================================================
    # COSTING
    # =====================================================

    @staticmethod
    def material_usage():
        total = Decimal("0.00")

        for item in ProductionMaterial.objects.all():
            total += item.total_cost

        return total

    @staticmethod
    def production_value():
        return (
            ProductionOutput.objects.aggregate(
                total=Coalesce(
                    Sum("product__selling_price"),
                    Decimal("0.00"),
                )
            )["total"]
            or Decimal("0.00")
        )

    @staticmethod
    def expected_profit():

        total = Decimal("0.00")

        quotations = Quotation.objects.filter(
            status="approved"
        )

        for quotation in quotations:

            total += (
                quotation.selling_price
                - quotation.total_cost
            )

        return total

    # =====================================================
    # DASHBOARD
    # =====================================================

    @classmethod
    def summary(cls):

        return {

            "active_jobs": cls.active_jobs(),

            "completed_jobs": cls.completed_jobs(),

            "completed_outputs": cls.completed_outputs(),

            "pending_quotations": cls.pending_quotations(),

            "approved_quotations": cls.approved_quotations(),

            "jobs_waiting_approval": cls.jobs_waiting_approval(),

            "jobs_in_production": cls.jobs_in_production(),

            "quality_queue": cls.quality_queue(),

            "open_issues": cls.open_issues(),

            "material_usage": cls.material_usage(),

            "production_value": cls.production_value(),

            "expected_profit": cls.expected_profit(),

            "delayed_jobs": cls.delayed_jobs(),

        }

    @classmethod
    def alerts(cls):

        alerts = []

        if cls.pending_quotations():

            alerts.append(
                f"{cls.pending_quotations()} quotation(s) waiting approval."
            )

        if cls.quality_queue():

            alerts.append(
                f"{cls.quality_queue()} production job(s) waiting quality inspection."
            )

        if cls.open_issues():

            alerts.append(
                f"{cls.open_issues()} unresolved production issue(s)."
            )

        if cls.delayed_jobs():

            alerts.append(
                f"{cls.delayed_jobs()} delayed production job(s)."
            )

        return alerts

    @classmethod
    def dashboard(cls):

        return {

            "cards": cls.summary(),

            "alerts": cls.alerts(),

        }

    @classmethod
    def report(cls, user=None, **kwargs):

        return {

            "title": "Furniture Manufacturing Report",

            "summary": cls.summary(),

            "rows": [],

            "charts": {

                "production": cls.jobs_in_production(),

                "quality": cls.quality_queue(),

                "profit": cls.expected_profit(),

            },

        }