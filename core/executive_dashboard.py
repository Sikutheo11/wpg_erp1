from core.providers.registry import ProviderRegistry
from core.models import ApprovalRequest, Notification, AuditLog


class ExecutiveDashboard:

    @staticmethod
    def get_business_summary():
        summary = {}

        for provider in ProviderRegistry.all():
            summary[provider.code] = {
                "name": provider.name,
                "summary": provider.summary(),
                "alerts": provider.alerts(),
            }

        return summary

    @staticmethod
    def get_pending_approvals():
        return ApprovalRequest.objects.filter(
            status="PENDING"
        ).order_by("-requested_at")[:10]

    @staticmethod
    def get_recent_notifications(user):
        return Notification.objects.filter(
            user=user
        ).order_by("-created_at")[:10]

    @staticmethod
    def get_recent_activity():
        return AuditLog.objects.select_related(
            "user"
        ).order_by("-created_at")[:10]

    @staticmethod
    def get_context(user):
        return {
            "business_summary": ExecutiveDashboard.get_business_summary(),
            "pending_approvals": ExecutiveDashboard.get_pending_approvals(),
            "recent_notifications": ExecutiveDashboard.get_recent_notifications(user),
            "recent_activity": ExecutiveDashboard.get_recent_activity(),
        }