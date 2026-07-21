from collections import defaultdict

from .models import (
    BusinessUnit,
    EnterpriseEngine,
)

from .permissions import PermissionService
from .bi_engine import BIEngine


class DashboardService:
    """
    WPG BOS Dashboard Engine.

    Responsibilities:
    - Build sidebar from Business Units and Enterprise Engines
    - Get KPI widgets from BI Engine
    """

    @staticmethod
    def get_business_unit_sidebar(user):
        features = PermissionService.get_allowed_business_unit_features(user)

        grouped = defaultdict(list)

        for feature in features:
            if feature.business_unit:
                grouped[feature.business_unit].append(feature)

        sidebar = []

        business_units = BusinessUnit.objects.filter(
            id__in=[bu.id for bu in grouped.keys()],
            is_active=True,
        ).order_by(
            "order",
            "name",
        )

        for business_unit in business_units:
            sidebar.append(
                {
                    "owner": business_unit,
                    "features": grouped[business_unit],
                    "type": "business_unit",
                }
            )

        return sidebar

    @staticmethod
    def get_engine_sidebar(user):
        features = PermissionService.get_allowed_engine_features(user)

        grouped = defaultdict(list)

        for feature in features:
            if feature.engine:
                grouped[feature.engine].append(feature)

        sidebar = []

        engines = EnterpriseEngine.objects.filter(
            id__in=[engine.id for engine in grouped.keys()],
            is_active=True,
        ).order_by(
            "order",
            "name",
        )

        for engine in engines:
            sidebar.append(
                {
                    "owner": engine,
                    "features": grouped[engine],
                    "type": "engine",
                }
            )

        return sidebar

    @staticmethod
    def get_sidebar(user):
        return {
            "business_units": DashboardService.get_business_unit_sidebar(user),
            "engines": DashboardService.get_engine_sidebar(user),
        }

    @staticmethod
    def get_kpi_widgets(user):
        return BIEngine.get_dashboard_widgets(user)

    @staticmethod
    def get_dashboard_context(user):
        sidebar = DashboardService.get_sidebar(user)

        return {
            "business_unit_sidebar": sidebar["business_units"],
            "engine_sidebar": sidebar["engines"],
            "kpi_widgets": DashboardService.get_kpi_widgets(user),
        }