from functools import wraps

from django.core.exceptions import ImproperlyConfigured, PermissionDenied

from core.permissions import PermissionService


class AgricultureFeatures:
    """Single source of truth for Agriculture feature codes."""

    DASHBOARD = "AGRICULTURE_DASHBOARD"
    FARMS = "AGRICULTURE_FARMS"
    HOUSES = "AGRICULTURE_HOUSES"
    BREEDS = "AGRICULTURE_BREEDS"
    OPERATIONS = "AGRICULTURE_OPERATIONS"
    FLOCKS = "AGRICULTURE_FLOCKS"
    DAILY_RECORDS = "AGRICULTURE_DAILY_RECORDS"
    EGG_PRODUCTION = "AGRICULTURE_EGG_PRODUCTION"
    FEEDING = "AGRICULTURE_FEEDING"
    HEALTH = "AGRICULTURE_HEALTH"
    MORTALITY = "AGRICULTURE_MORTALITY"
    INCUBATION = "AGRICULTURE_INCUBATION"
    REPORTS = "AGRICULTURE_REPORTS"

    OPERATION_SUBMIT = "AGRICULTURE_OPERATION_SUBMIT"
    OPERATION_APPROVE = "AGRICULTURE_OPERATION_APPROVE"
    OPERATION_START = "AGRICULTURE_OPERATION_START"
    OPERATION_HOLD = "AGRICULTURE_OPERATION_HOLD"
    OPERATION_RESUME = "AGRICULTURE_OPERATION_RESUME"
    OPERATION_COMPLETE = "AGRICULTURE_OPERATION_COMPLETE"
    OPERATION_CANCEL = "AGRICULTURE_OPERATION_CANCEL"


VALID_ACTIONS = {"view", "add", "edit", "delete", "approve"}


def user_can_access_agriculture_feature(
    user,
    feature_code,
    *,
    action="view",
):
    """
    Return whether a user may perform an action on an Agriculture feature.

    Core PermissionService remains the authority for superuser, Group,
    RoleFeature and action-level decisions.
    """
    if action not in VALID_ACTIONS:
        raise ValueError(
            f"Unsupported permission action '{action}'. "
            f"Expected one of {sorted(VALID_ACTIONS)}."
        )

    if user is None or not getattr(user, "is_authenticated", False):
        return False

    return PermissionService.user_can_access_feature(
        user,
        feature_code,
        action=action,
    )


def require_agriculture_feature(user, feature_code, *, action="view"):
    """Raise PermissionDenied unless the user has the requested permission."""
    if user_can_access_agriculture_feature(
        user,
        feature_code,
        action=action,
    ):
        return True

    readable_feature = feature_code.replace("AGRICULTURE_", "").replace(
        "_",
        " ",
    )
    raise PermissionDenied(
        f"You do not have permission to {action} "
        f"Agriculture {readable_feature.lower()}."
    )


def require_feeding_finance_post(user):
    return require_agriculture_feature(
        user,
        AgricultureFeatures.FEEDING,
        action="approve",
    )


def require_health_finance_post(user):
    return require_agriculture_feature(
        user,
        AgricultureFeatures.HEALTH,
        action="approve",
    )


def agriculture_feature_required(feature_code, action="view"):
    """Decorator for function-based Agriculture views."""
    if action not in VALID_ACTIONS:
        raise ValueError(
            f"Unsupported permission action '{action}'. "
            f"Expected one of {sorted(VALID_ACTIONS)}."
        )

    def decorator(view_function):
        @wraps(view_function)
        def wrapped_view(request, *args, **kwargs):
            require_agriculture_feature(
                request.user,
                feature_code,
                action=action,
            )
            return view_function(request, *args, **kwargs)

        return wrapped_view

    return decorator


class AgricultureFeaturePermissionMixin:
    """Permission mixin for any future class-based Agriculture views."""

    agriculture_feature_code = None
    agriculture_permission_action = "view"

    def dispatch(self, request, *args, **kwargs):
        if not self.agriculture_feature_code:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define "
                "agriculture_feature_code."
            )

        require_agriculture_feature(
            request.user,
            self.agriculture_feature_code,
            action=self.agriculture_permission_action,
        )
        return super().dispatch(request, *args, **kwargs)


def agriculture_permission_context(user):
    """
    Permission flags for showing or hiding Agriculture actions in templates.

    These flags improve the UI only. Views and services remain responsible for
    enforcing authorization.
    """
    checks = {
        "can_view_dashboard": (AgricultureFeatures.DASHBOARD, "view"),
        "can_add_farm": (AgricultureFeatures.FARMS, "add"),
        "can_edit_farm": (AgricultureFeatures.FARMS, "edit"),
        "can_add_house": (AgricultureFeatures.HOUSES, "add"),
        "can_add_breed": (AgricultureFeatures.BREEDS, "add"),
        "can_add_operation": (AgricultureFeatures.OPERATIONS, "add"),
        "can_add_flock": (AgricultureFeatures.FLOCKS, "add"),
        "can_record_daily": (AgricultureFeatures.DAILY_RECORDS, "add"),
        "can_record_eggs": (AgricultureFeatures.EGG_PRODUCTION, "add"),
        "can_record_feeding": (AgricultureFeatures.FEEDING, "add"),
        "can_record_health": (AgricultureFeatures.HEALTH, "add"),
        "can_record_mortality": (AgricultureFeatures.MORTALITY, "add"),
        "can_manage_incubation": (AgricultureFeatures.INCUBATION, "add"),
        "can_approve_operation": (
            AgricultureFeatures.OPERATION_APPROVE,
            "approve",
        ),
    }

    return {
        key: user_can_access_agriculture_feature(
            user,
            feature_code,
            action=action,
        )
        for key, (feature_code, action) in checks.items()
    }


# Common decorators used by agriculture/views.py.
agriculture_dashboard_required = agriculture_feature_required(
    AgricultureFeatures.DASHBOARD,
    "view",
)
farm_view_required = agriculture_feature_required(
    AgricultureFeatures.FARMS,
    "view",
)
farm_add_required = agriculture_feature_required(
    AgricultureFeatures.FARMS,
    "add",
)
farm_edit_required = agriculture_feature_required(
    AgricultureFeatures.FARMS,
    "edit",
)
house_add_required = agriculture_feature_required(
    AgricultureFeatures.HOUSES,
    "add",
)

house_add_required = agriculture_feature_required(
    AgricultureFeatures.HOUSES,
    "add",
)

house_edit_required = agriculture_feature_required(
    AgricultureFeatures.HOUSES,
    "edit",
)

breed_view_required = agriculture_feature_required(
    AgricultureFeatures.BREEDS,
    "view",
)
breed_add_required = agriculture_feature_required(
    AgricultureFeatures.BREEDS,
    "add",
)
operation_view_required = agriculture_feature_required(
    AgricultureFeatures.OPERATIONS,
    "view",
)
operation_add_required = agriculture_feature_required(
    AgricultureFeatures.OPERATIONS,
    "add",
)
flock_view_required = agriculture_feature_required(
    AgricultureFeatures.FLOCKS,
    "view",
)
flock_add_required = agriculture_feature_required(
    AgricultureFeatures.FLOCKS,
    "add",
)
daily_record_add_required = agriculture_feature_required(
    AgricultureFeatures.DAILY_RECORDS,
    "add",
)
egg_production_add_required = agriculture_feature_required(
    AgricultureFeatures.EGG_PRODUCTION,
    "add",
)
feeding_add_required = agriculture_feature_required(
    AgricultureFeatures.FEEDING,
    "add",
)
health_add_required = agriculture_feature_required(
    AgricultureFeatures.HEALTH,
    "add",
)
mortality_add_required = agriculture_feature_required(
    AgricultureFeatures.MORTALITY,
    "add",
)
incubation_view_required = agriculture_feature_required(
    AgricultureFeatures.INCUBATION,
    "view",
)
incubation_add_required = agriculture_feature_required(
    AgricultureFeatures.INCUBATION,
    "add",
)
incubation_edit_required = agriculture_feature_required(
    AgricultureFeatures.INCUBATION,
    "edit",
)
reports_view_required = agriculture_feature_required(
    AgricultureFeatures.REPORTS,
    "view",
)