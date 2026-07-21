from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import Notification


User = get_user_model()


class NotificationService:
    """
    Central notification service for WPG BOS.
    Accepts either User or Employee recipients.
    """

    @staticmethod
    def normalize_user(candidate):
        if candidate is None:
            return None

        # Already a User
        if isinstance(candidate, User):
            return candidate

        # Employee or another object linked to User
        related_user = getattr(candidate, "user", None)

        if isinstance(related_user, User):
            return related_user

        return None

    @classmethod
    def notify_users(
        cls,
        users,
        title,
        message,
        level="INFO",
        url="",
    ):
        created = []
        notified_user_ids = set()

        for candidate in users or []:
            user = cls.normalize_user(candidate)

            if user is None:
                continue

            if user.pk in notified_user_ids:
                continue

            notified_user_ids.add(user.pk)

            created.append(
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    level=level,
                    url=url,
                )
            )

        return created

    @classmethod
    def notify_groups(
        cls,
        group_names,
        title,
        message,
        level="INFO",
        url="",
    ):
        users = set()

        groups = Group.objects.filter(
            name__in=group_names or []
        ).prefetch_related("user_set")

        for group in groups:
            users.update(group.user_set.all())

        return cls.notify_users(
            users=users,
            title=title,
            message=message,
            level=level,
            url=url,
        )

    @classmethod
    def notify_object_owner(
        cls,
        obj,
        title,
        message,
        level="INFO",
        url="",
    ):
        if obj is None:
            return []

        owner_fields = (
            "user",
            "created_by",
            "requested_by",
            "owner",
            "assigned_to",
            "prepared_by",
            "approved_by",
            "produced_by",
            "performed_by",
            "employee",
        )

        for field_name in owner_fields:
            candidate = getattr(obj, field_name, None)
            user = cls.normalize_user(candidate)

            if user is not None:
                return cls.notify_users(
                    users=[user],
                    title=title,
                    message=message,
                    level=level,
                    url=url,
                )

        return []

    @staticmethod
    def unread_count(user):
        if not user or not user.is_authenticated:
            return 0

        return Notification.objects.filter(
            user=user,
            is_read=False,
        ).count()

    @staticmethod
    def mark_as_read(notification):
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return notification

    @staticmethod
    def mark_all_as_read(user):
        return Notification.objects.filter(
            user=user,
            is_read=False,
        ).update(is_read=True)