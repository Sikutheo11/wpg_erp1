from .dashboard import DashboardService


def dashboard_context(request):
    if not request.user.is_authenticated:
        return {
            "account_shell_template": "ecommerce/base_ecommerce.html",
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
        is_customer = (
            not request.user.is_superuser
            and request.user.groups.filter(name="Customer").exists()
        )
        unread_notifications = request.user.notifications.filter(
            is_read=False,
        ).order_by("-created_at")
        context.update({
            "account_shell_template": (
                "ecommerce/base_ecommerce.html"
                if is_customer
                else "base_dashboard.html"
            ),
            "unread_notification_count": unread_notifications.count(),
            "unread_notifications": unread_notifications[:5],
        })
        return context

    except Exception:
        return {
            "account_shell_template": (
                "ecommerce/base_ecommerce.html"
                if request.user.groups.filter(name="Customer").exists()
                else "base_dashboard.html"
            ),
            "business_unit_sidebar": [],
            "engine_sidebar": [],
            "dashboard_cards": [],
            "unread_notification_count": 0,
            "unread_notifications": [],
        }
