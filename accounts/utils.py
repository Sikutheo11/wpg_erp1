from django.shortcuts import redirect
from django.urls import NoReverseMatch

from core.permissions import PermissionService


def redirect_by_role(user):

    # Super Admin
    if user.is_superuser:

        return redirect(
            "core:dashboard"
        )


    access_profiles = (
        user.groups.filter(
            access_profile__landing_feature__is_active=True,
        )
        .select_related("access_profile__landing_feature")
        .order_by("access_profile__priority", "name")
    )
    for group in access_profiles:
        landing_feature = group.access_profile.landing_feature
        if not PermissionService.user_can_access_feature(
            user,
            landing_feature.code,
        ):
            continue
        try:
            return redirect(landing_feature.url_name)
        except NoReverseMatch:
            continue

    # Safe fallback for groups that have not configured a landing feature.
    feature = (
        PermissionService.get_allowed_features(user)
        .exclude(url_name="")
        .first()
    )

    if feature:
        try:
            return redirect(feature.url_name)
        except NoReverseMatch:
            pass

    if user.groups.filter(name="Customer").exists():

        return redirect(
            "core:customer_dashboard"
        )


    # Default

    return redirect(
        "profile"
    )
