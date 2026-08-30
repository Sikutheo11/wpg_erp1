from django.apps import AppConfig



class CoreConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "core"

    def ready(self):
        from core.internal_codes import install_model_form_code_policy
        install_model_form_code_policy()
        import core.reports
        import furniture.providers
        import core.job_investment_models  # noqa: F401
        import core.job_investment_finance_models  # noqa: F401
        import core.confidential_capital_models  # noqa: F401
        import core.confidential_funding_offer_models  # noqa: F401
