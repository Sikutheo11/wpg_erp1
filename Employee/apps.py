from django.apps import AppConfig


class EmployeeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"

    name = "Employee"


    def ready(self):
        from core.dashboard_registry import register_dashboard
        from core.module_registry import register_module
        from .dashboard import get_employee_dashboard


        register_dashboard("employee", get_employee_dashboard)


        register_module(
            name="Employee",
            url_name="employee_dashboard",
            icon="fa-users",
            permission="employee.view_dashboard"
        )