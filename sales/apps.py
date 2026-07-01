from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sales"


    def ready(self):

        from core.dashboard_registry import register_dashboard
        from core.module_registry import register_module
        from .dashboard import get_sales_dashboard


        # ==================================
        # REGISTER DASHBOARD
        # ==================================

        register_dashboard(
            "sales",
            get_sales_dashboard
        )


        # ==================================
        # REGISTER MODULE
        # ==================================

        register_module(
            name="Sales",
            url_name="sales:sales_dashboard",
            icon="fa-shopping-cart",
            permission="sales.view_dashboard"
        )