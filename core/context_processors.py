from .dashboard import DashboardService


def dashboard_context(request):
    if not request.user.is_authenticated:
        return {
            "business_unit_sidebar": [],
            "engine_sidebar": [],
            "dashboard_cards": [],
        }

    try:
        return DashboardService.get_dashboard_context(
            request.user
        )

    except Exception:
        return {
            "business_unit_sidebar": [],
            "engine_sidebar": [],
            "dashboard_cards": [],
        }