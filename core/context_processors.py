from .dashboard import DashboardService


def dashboard_context(request):
    if not request.user.is_authenticated:
        return {
            "business_unit_sidebar": [],
            "engine_sidebar": [],
            "dashboard_cards": [],
            "unread_notification_count": 0,
            "unread_notifications": [],
        }

    try:
        context = DashboardService.get_dashboard_context(
            request.user
        )
        unread_notifications = request.user.notifications.filter(
            is_read=False,
        ).order_by("-created_at")
        context.update({
            "unread_notification_count": unread_notifications.count(),
            "unread_notifications": unread_notifications[:5],
        })
        return context

    except Exception:
        return {
            "business_unit_sidebar": [],
            "engine_sidebar": [],
            "dashboard_cards": [],
            "unread_notification_count": 0,
            "unread_notifications": [],
        }
