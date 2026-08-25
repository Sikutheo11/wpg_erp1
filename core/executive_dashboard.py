from core.providers.registry import ProviderRegistry
from core.models import ApprovalRequest, Notification, AuditLog
from core.permissions import PermissionService


class ExecutiveDashboard:

    @staticmethod
    def get_business_summary(user):
        summary = {}

        if PermissionService.is_super_user(user):
            allowed_provider_codes = None
        else:
            business_unit_codes = set(
                PermissionService.get_allowed_business_unit_features(user)
                .values_list("business_unit__code", flat=True)
            )
            engine_codes = set(
                PermissionService.get_allowed_engine_features(user)
                .values_list("engine__code", flat=True)
            )
            allowed_provider_codes = business_unit_codes | engine_codes

        for provider in ProviderRegistry.all():
            if (
                allowed_provider_codes is not None
                and provider.code not in allowed_provider_codes
            ):
                continue
            summary[provider.code] = {
                "name": provider.name,
                "summary": provider.summary(),
                "alerts": provider.alerts(),
            }

        return summary

    @staticmethod
    def get_pending_approvals(user):
        approvals = ApprovalRequest.objects.filter(status="PENDING")
        if not PermissionService.is_super_user(user):
            approvals = approvals.filter(requested_by=user)
        return approvals.order_by("-requested_at")[:10]

    @staticmethod
    def get_recent_notifications(user):
        return Notification.objects.filter(
            user=user
        ).order_by("-created_at")[:10]

    @staticmethod
    def get_recent_activity(user):
        activity = AuditLog.objects.select_related("user")
        if not PermissionService.is_super_user(user):
            activity = activity.filter(user=user)
        return activity.order_by("-created_at")[:10]

    @staticmethod
    def get_context(user):
        is_executive = PermissionService.is_super_user(user)
        return {
            "dashboard_title": (
                "Executive Dashboard" if is_executive else "My Work Dashboard"
            ),
            "dashboard_subtitle": (
                "Company-wide intelligence overview"
                if is_executive
                else "Information and actions available for your role"
            ),
            "business_summary": ExecutiveDashboard.get_business_summary(user),
            "pending_approvals": ExecutiveDashboard.get_pending_approvals(user),
            "recent_notifications": ExecutiveDashboard.get_recent_notifications(user),
            "recent_activity": ExecutiveDashboard.get_recent_activity(user),
        }
