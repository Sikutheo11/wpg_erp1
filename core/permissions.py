from .models import Feature, RoleFeature


class PermissionService:
    """
    WPG BOS Permission Engine.

    Source of truth:
    Django Group -> RoleFeature -> Feature

    Feature may belong to:
    - BusinessUnit
    - EnterpriseEngine
    """

    @staticmethod
    def get_user_groups(user):
        if not user or not user.is_authenticated:
            return []
        return user.groups.all()

    @staticmethod
    def is_super_user(user):
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or getattr(user, "is_superadmin", False)
                or getattr(user, "is_admin", False)
            )
        )

    @staticmethod
    def user_can_access_feature(user, feature_code, action="view"):

        if PermissionService.is_super_user(user):
            return True

        groups = PermissionService.get_user_groups(user)

        field_map = {
            "view": "can_view",
            "add": "can_add",
            "edit": "can_edit",
            "delete": "can_delete",
            "approve": "can_approve",
        }

        permission_field = field_map.get(action, "can_view")

        filters = {
            "role__in": groups,
            "feature__code": feature_code,
            "feature__is_active": True,
            permission_field: True,
        }

        return RoleFeature.objects.filter(**filters).exists()

    @staticmethod
    def get_allowed_features(user):

        if PermissionService.is_super_user(user):
            return Feature.objects.filter(
                is_active=True
            ).select_related(
                "business_unit",
                "engine",
            ).order_by(
                "order",
                "name",
            )

        groups = PermissionService.get_user_groups(user)

        feature_ids = RoleFeature.objects.filter(
            role__in=groups,
            can_view=True,
            feature__is_active=True,
        ).values_list(
            "feature_id",
            flat=True
        ).distinct()

        return Feature.objects.filter(
            id__in=feature_ids,
            is_active=True
        ).select_related(
            "business_unit",
            "engine",
        ).order_by(
            "order",
            "name",
        )

    @staticmethod
    def get_allowed_business_unit_features(user):

        return PermissionService.get_allowed_features(
            user
        ).filter(
            business_unit__isnull=False,
            business_unit__is_active=True,
        ).order_by(
            "business_unit__order",
            "order",
            "name",
        )

    @staticmethod
    def get_allowed_engine_features(user):

        return PermissionService.get_allowed_features(
            user
        ).filter(
            engine__isnull=False,
            engine__is_active=True,
        ).order_by(
            "engine__order",
            "order",
            "name",
        )