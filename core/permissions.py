from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import Feature, Module, RoleFeature, RoleModule


class PermissionService:
    """
    WPG BOS Permission Engine.

    Source of truth:
    Django Group -> Django Permission -> Feature

    RoleFeature remains a compatibility fallback only while existing roles
    are migrated to Django permissions.

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

        field_map = {
            "view": ("view_permission", "can_view"),
            "add": ("add_permission", "can_add"),
            "edit": ("change_permission", "can_edit"),
            "change": ("change_permission", "can_edit"),
            "delete": ("delete_permission", "can_delete"),
            "approve": ("approve_permission", "can_approve"),
        }

        permission_attribute, legacy_field = field_map.get(
            action,
            field_map["view"],
        )

        try:
            feature = Feature.objects.get(
                code=feature_code,
                is_active=True,
            )
        except Feature.DoesNotExist:
            return False

        permission_name = getattr(feature, permission_attribute, "").strip()
        if permission_name:
            return user.has_perm(permission_name)

        groups = PermissionService.get_user_groups(user)

        filters = {
            "role__in": groups,
            "feature": feature,
            legacy_field: True,
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
        django_permissions = user.get_all_permissions()

        feature_ids = RoleFeature.objects.filter(
            role__in=groups,
            can_view=True,
            feature__is_active=True,
        ).values_list(
            "feature_id",
            flat=True
        ).distinct()

        permission_filter = Q(pk__in=[])
        for permission_name in django_permissions:
            permission_filter |= Q(view_permission=permission_name)

        return Feature.objects.filter(
            Q(view_permission="", id__in=feature_ids)
            | permission_filter,
            is_active=True,
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

    @staticmethod
    def user_has_permission(
        user,
        permission_name,
        *,
        feature_code=None,
        action="view",
    ):
        if PermissionService.is_super_user(user):
            return True

        if not user or not user.is_authenticated:
            return False

        if user.has_perm(permission_name):
            return True

        if feature_code:
            return PermissionService.user_can_access_feature(
                user,
                feature_code,
                action,
            )

        return False

    @staticmethod
    def user_can_view_module(user, module_code):
        if PermissionService.is_super_user(user):
            return True

        try:
            module = Module.objects.get(code=module_code, is_active=True)
        except Module.DoesNotExist:
            return False

        if module.permission:
            return user.has_perm(module.permission)

        return RoleModule.objects.filter(
            role__in=PermissionService.get_user_groups(user),
            module=module,
            can_view=True,
        ).exists()


def wpg_permission_required(
    permission_name,
    *,
    feature_code=None,
    action="view",
):
    """Protect a view with Django Group permissions and legacy fallback."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(),
                    settings.LOGIN_URL,
                )

            if PermissionService.user_has_permission(
                request.user,
                permission_name,
                feature_code=feature_code,
                action=action,
            ):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied

        return wrapped

    return decorator
