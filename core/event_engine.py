# ==========================================
# WPG BOS
# Event Engine
# ==========================================

from django.utils import timezone



class EventEngine:
    """
    Central event dispatcher for notifications, audit logs,
    KPI refresh and future integrations.
    """

    @staticmethod
    def build_event(
        event_code,
        actor=None,
        obj=None,
        title="",
        message="",
        level="INFO",
        metadata=None,
    ):
        return {
            "event_code": event_code,
            "actor": actor,
            "object_app": obj._meta.app_label if obj else "",
            "object_model": obj._meta.model_name if obj else "",
            "object_id": str(obj.pk) if obj and obj.pk else "",
            "title": title,
            "message": message,
            "level": level,
            "metadata": metadata or {},
            "created_at": timezone.now(),
        }

    @staticmethod
    def dispatch(
        event_code,
        actor=None,
        obj=None,
        title="",
        message="",
        level="INFO",
        metadata=None,
        notify_users=None,
        notify_groups=None,
        notify_owner=False,
    ):
        event = EventEngine.build_event(
            event_code=event_code,
            actor=actor,
            obj=obj,
            title=title,
            message=message,
            level=level,
            metadata=metadata,
        )

        EventEngine.notify(
            event=event,
            notify_users=notify_users or [],
            notify_groups=notify_groups or [],
            notify_owner=notify_owner,
            obj=obj,
        )

        EventEngine.audit(event)

        return event

    @staticmethod
    def notify(
        event,
        notify_users=None,
        notify_groups=None,
        notify_owner=False,
        obj=None,
    ):
        from .notification_service import NotificationService

        NotificationService.notify_users(
            users=notify_users or [],
            title=event["title"] or event["event_code"],
            message=event["message"],
            level=event["level"],
            url="",
        )

        NotificationService.notify_groups(
            group_names=notify_groups or [],
            title=event["title"] or event["event_code"],
            message=event["message"],
            level=event["level"],
            url="",
        )

        if notify_owner and obj:
            NotificationService.notify_object_owner(
                obj=obj,
                title=event["title"] or event["event_code"],
                message=event["message"],
                level=event["level"],
                url="",
            )

    @staticmethod
    def audit(event):
        from .models import AuditLog

        AuditLog.objects.create(
            user=event["actor"],
            action="UPDATE",
            app_label=event["object_app"] or "core",
            model_name=event["object_model"] or "event",
            object_id=event["object_id"],
            description=f"{event['event_code']} - {event['message']}",
            new_data=event["metadata"],
        )