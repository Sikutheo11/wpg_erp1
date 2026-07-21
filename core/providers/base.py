"""
==========================================
WPG BOS
Base Provider
==========================================
"""


class BaseProvider:
    """
    Base class for every Business Provider.

    Every provider should inherit this class.
    """

    code = ""
    name = ""

    # -----------------------------
    # Dashboard
    # -----------------------------

    @classmethod
    def dashboard(cls):
        """
        Return dashboard data.
        """
        return {}

    # -----------------------------
    # KPIs
    # -----------------------------

    @classmethod
    def kpis(cls):
        """
        Return KPI values.
        """
        return {}

    # -----------------------------
    # Report
    # -----------------------------

    @classmethod
    def report(cls, user=None, **kwargs):
        """
        Return report dictionary.
        """
        return {}

    # -----------------------------
    # Charts
    # -----------------------------

    @classmethod
    def charts(cls):
        return {}

    # -----------------------------
    # Alerts
    # -----------------------------

    @classmethod
    def alerts(cls):
        return []

    # -----------------------------
    # Summary
    # -----------------------------

    @classmethod
    def summary(cls):
        return {}