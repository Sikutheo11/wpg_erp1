from django.apps import AppConfig


class FurnitureConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"
    name = "furniture"


    def ready(self):
        from core.dashboard_registry import register_dashboard
        from core.module_registry import register_module
        from .dashboard import get_furniture_dashboard


        # Register Furniture Dashboard

        register_dashboard(
            "furniture",
            get_furniture_dashboard
        )


        # Register Furniture Module

        register_module(
            name="Furniture",
            url_name="furniture_dashboard",
            icon="fa-chair",
            permission="furniture.view_dashboard"
        )

        # =========================
        # Register Dashboard
        # =========================

        register_dashboard(
            "furniture",
            get_furniture_dashboard
        )