from django.apps import AppConfig


class ConstructionConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "Construction"


    def ready(self):

        from core.dashboard_registry import register_dashboard
        from core.module_registry import register_module
        from .dashboard import get_construction_dashboard


        # Register dashboard

        register_dashboard(
            "construction",
            get_construction_dashboard
        )


        # Register module

        register_module(
            name="Construction",
            url_name="construction_dashboard",
            icon="fa-building",
            permission="construction.view_dashboard"
        )