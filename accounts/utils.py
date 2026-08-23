from django.shortcuts import redirect
from django.urls import NoReverseMatch

from core.permissions import PermissionService


def redirect_by_role(user):

    # Super Admin
    if user.is_superuser:

        return redirect(
            "core:dashboard"
        )


    # Roles are Django Groups. The first permitted feature with a URL is the
    # user's landing page; no Group name is hardcoded for employee roles.
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
