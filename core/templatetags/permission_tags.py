from django import template
from django.urls import reverse, NoReverseMatch
from core.permissions import PermissionService

register = template.Library()


# ======================================================
# FEATURE PERMISSIONS
# ======================================================

@register.filter
def can_view(user, feature_code):
    return PermissionService.user_can_access_feature(
        user=user,
        feature_code=feature_code,
        action="view",
    )


@register.filter
def can_add(user, feature_code):
    return PermissionService.user_can_access_feature(
        user=user,
        feature_code=feature_code,
        action="add",
    )


@register.filter
def can_edit(user, feature_code):
    return PermissionService.user_can_access_feature(
        user=user,
        feature_code=feature_code,
        action="edit",
    )


@register.filter
def can_delete(user, feature_code):
    return PermissionService.user_can_access_feature(
        user=user,
        feature_code=feature_code,
        action="delete",
    )


@register.filter
def can_approve(user, feature_code):
    return PermissionService.user_can_access_feature(
        user=user,
        feature_code=feature_code,
        action="approve",
    )


# ======================================================
# MODULE PERMISSIONS
# ======================================================

@register.filter
def can_view_module(user, module_code):
    return PermissionService.user_can_view_module(
        user=user,
        module_code=module_code,
    )

@register.simple_tag
def safe_url(url_name):
    if not url_name:
        return "#"

    try:
        return reverse(url_name)
    except NoReverseMatch:
        return "#"