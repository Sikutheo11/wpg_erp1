from django.apps import AppConfig



class CoreConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "core"

    def ready(self):
        import core.reports
        import furniture.providers
        import core.job_investment_models  # noqa: F401
        import core.job_investment_finance_models  # noqa: F401
