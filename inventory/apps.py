from django.apps import AppConfig



class InventoryConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"



    def ready(self):

        from core.dashboard_registry import register_dashboard
        from core.module_registry import register_module
        from .dashboard import get_inventory_dashboard



        # Dashboard registration

        register_dashboard(
            "inventory", get_inventory_dashboard
        )
        # Module registration

        register_module(

            name="Inventory",

            url_name="inventory:inventory_dashboard",

            icon="fa-boxes",

            permission="inventory.view_dashboard"

        )