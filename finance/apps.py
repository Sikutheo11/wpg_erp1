from django.apps import AppConfig


class FinanceConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "finance"


    def ready(self):

        from core.dashboard_registry import register_dashboard
        from core.module_registry import register_module

        from .dashboard import get_finance_dashboard


        # Register Dashboard

        register_dashboard(
            "finance",
            get_finance_dashboard
        )


        # Register Sidebar Module

        register_module(
            name="Finance",
            url_name="finance:finance_dashboard",
            icon="fa-money-bill",
            permission="finance.view_dashboard"
        )