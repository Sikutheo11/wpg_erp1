"""
==========================================
WPG BOS
Provider Registry
==========================================
"""


class ProviderRegistry:

    _providers = {}

    # ======================================
    # Register
    # ======================================

    @classmethod
    def register(cls, provider):

        cls._providers[
            provider.code
        ] = provider

        return provider

    # ======================================
    # Get
    # ======================================

    @classmethod
    def get(cls, code):

        provider = cls._providers.get(code)

        if provider is None:
            raise ValueError(
                f"Provider '{code}' is not registered."
            )

        return provider

    # ======================================
    # Dashboard
    # ======================================

    @classmethod
    def dashboard(cls, code):

        provider = cls.get(code)

        return provider.dashboard()

    # ======================================
    # KPIs
    # ======================================

    @classmethod
    def kpis(cls, code):

        provider = cls.get(code)

        return provider.kpis()

    # ======================================
    # Report
    # ======================================

    @classmethod
    def report(cls, code, user=None, **kwargs):

        provider = cls.get(code)

        return provider.report(
            user=user,
            **kwargs,
        )

    # ======================================
    # Alerts
    # ======================================

    @classmethod
    def alerts(cls, code):

        provider = cls.get(code)

        return provider.alerts()

    # ======================================
    # Charts
    # ======================================

    @classmethod
    def charts(cls, code):

        provider = cls.get(code)

        return provider.charts()

    # ======================================
    # Summary
    # ======================================

    @classmethod
    def summary(cls, code):

        provider = cls.get(code)

        return provider.summary()

    # ======================================
    # List Providers
    # ======================================

    @classmethod
    def all(cls):

        return list(
            cls._providers.values()
        )

    # ======================================
    # Codes
    # ======================================

    @classmethod
    def codes(cls):

        return list(
            cls._providers.keys()
        )