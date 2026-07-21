# ==========================================
# WPG BOS
# Business Intelligence Engine
# ==========================================

from .models import KPIWidget
from .providers.registry import ProviderRegistry
# Import providers so they auto-register
import core.providers  # noqa


class BIEngine:
    """
    WPG Business Intelligence Engine.

    BIEngine is now an orchestrator:
    KPIWidget.data_source -> ProviderRegistry -> Provider method
    """

    DATA_SOURCE_MAP = {
        "finance.total_income": ("FINANCE", "total_income"),
        "finance.total_expense": ("FINANCE", "total_expense"),
        "finance.net_profit": ("FINANCE", "net_profit"),

        "inventory.products": ("INVENTORY", "products"),
        "inventory.raw_materials": ("INVENTORY", "raw_materials"),
        "inventory.stock_alerts": ("INVENTORY", "stock_alerts"),

        "orders.total_orders": ("ORDER", "total_orders"),
        "orders.pending_orders": ("ORDER", "pending_orders"),

        "furniture.active_jobs": ("FURNITURE", "active_jobs"),
        "furniture.completed_outputs": ("FURNITURE", "completed_outputs"),
        "furniture.material_usage": ("FURNITURE", "material_usage"),

        "construction.active_projects": ("CONSTRUCTION", "active_projects"),
        "construction.delayed_projects": ("CONSTRUCTION", "delayed_projects"),
        "construction.budget_used": ("CONSTRUCTION", "budget_used"),

        "marketplace.online_orders": ("MARKETPLACE", "online_orders"),
        "marketplace.online_products": ("MARKETPLACE", "online_products"),

        "people.employees": ("PEOPLE", "employees"),
        "people.attendance_today": ("PEOPLE", "attendance_today"),

        "agriculture.egg_production": ("AGRICULTURE", "egg_production"),
        "agriculture.mortality": ("AGRICULTURE", "mortality"),
    }

    @classmethod
    def get_dashboard_widgets(cls, user=None):
        widgets = KPIWidget.objects.filter(
            is_active=True
        ).select_related(
            "business_unit",
            "engine"
        ).order_by(
            "order",
            "title"
        )

        return [
            cls.resolve_widget(widget)
            for widget in widgets
        ]

    @classmethod
    def resolve_widget(cls, widget):
        return {
            "id": widget.id,
            "title": widget.title,
            "code": widget.code,
            "widget_type": widget.widget_type,
            "icon": widget.icon,
            "color": widget.color,
            "value": cls.resolve_data_source(widget.data_source),
            "business_unit": widget.business_unit,
            "engine": widget.engine,
        }

    @classmethod
    def resolve_data_source(cls, source):
        provider_info = cls.DATA_SOURCE_MAP.get(source)

        if not provider_info:
            return 0

        provider_code, method_name = provider_info

        try:
            provider = ProviderRegistry.get(provider_code)
            method = getattr(provider, method_name)
            return method()

        except Exception:
            return 0

    # ==================================================
    # Backward-compatible helper methods
    # ==================================================

    @classmethod
    def finance_total_income(cls):
        return cls.resolve_data_source("finance.total_income")

    @classmethod
    def finance_total_expense(cls):
        return cls.resolve_data_source("finance.total_expense")

    @classmethod
    def finance_net_profit(cls):
        return cls.resolve_data_source("finance.net_profit")

    @classmethod
    def inventory_products(cls):
        return cls.resolve_data_source("inventory.products")

    @classmethod
    def inventory_raw_materials(cls):
        return cls.resolve_data_source("inventory.raw_materials")

    @classmethod
    def inventory_stock_alerts(cls):
        return cls.resolve_data_source("inventory.stock_alerts")

    @classmethod
    def orders_total_orders(cls):
        return cls.resolve_data_source("orders.total_orders")

    @classmethod
    def orders_pending_orders(cls):
        return cls.resolve_data_source("orders.pending_orders")

    @classmethod
    def furniture_active_jobs(cls):
        return cls.resolve_data_source("furniture.active_jobs")

    @classmethod
    def furniture_completed_outputs(cls):
        return cls.resolve_data_source("furniture.completed_outputs")

    @classmethod
    def furniture_material_usage(cls):
        return cls.resolve_data_source("furniture.material_usage")

    @classmethod
    def construction_active_projects(cls):
        return cls.resolve_data_source("construction.active_projects")

    @classmethod
    def construction_delayed_projects(cls):
        return cls.resolve_data_source("construction.delayed_projects")

    @classmethod
    def construction_budget_used(cls):
        return cls.resolve_data_source("construction.budget_used")

    @classmethod
    def marketplace_online_orders(cls):
        return cls.resolve_data_source("marketplace.online_orders")

    @classmethod
    def marketplace_online_products(cls):
        return cls.resolve_data_source("marketplace.online_products")

    @classmethod
    def people_employees(cls):
        return cls.resolve_data_source("people.employees")

    @classmethod
    def people_attendance_today(cls):
        return cls.resolve_data_source("people.attendance_today")

    @classmethod
    def agriculture_egg_production(cls):
        return cls.resolve_data_source("agriculture.egg_production")

    @classmethod
    def agriculture_mortality(cls):
        return cls.resolve_data_source("agriculture.mortality")