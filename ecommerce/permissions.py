from functools import wraps

from django.core.exceptions import ImproperlyConfigured, PermissionDenied

from core.permissions import PermissionService


class MarketplaceFeatures:
    """Single source of truth for Marketplace feature codes."""

    DASHBOARD = "MARKETPLACE_DASHBOARD"
    SHOP = "MARKETPLACE_SHOP"
    PRODUCTS = "MARKETPLACE_PRODUCTS"
    ORDERS = "MARKETPLACE_ORDERS"
    SELLERS = "MARKETPLACE_SELLERS"
    COMMISSIONS = "MARKETPLACE_COMMISSIONS"
    SETTLEMENTS = "MARKETPLACE_SETTLEMENTS"
    PAYMENTS = "MARKETPLACE_PAYMENTS"
    REPORTS = "MARKETPLACE_REPORTS"


VALID_ACTIONS = {"view", "add", "edit", "delete", "approve"}


def user_can_access_marketplace_feature(
    user,
    feature_code,
    *,
    action="view",
):
    """Return whether Core grants an action on a Marketplace feature."""
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


def require_marketplace_feature(
    user,
    feature_code,
    *,
    action="view",
):
    """Raise PermissionDenied unless Core grants the requested action."""
    if user_can_access_marketplace_feature(
        user,
        feature_code,
        action=action,
    ):
        return True

    readable_feature = feature_code.replace(
        "MARKETPLACE_",
        "",
    ).replace("_", " ")
    raise PermissionDenied(
        f"You do not have permission to {action} "
        f"Marketplace {readable_feature.lower()}."
    )


def marketplace_feature_required(feature_code, action="view"):
    """Decorator for function-based Marketplace management views."""
    if action not in VALID_ACTIONS:
        raise ValueError(
            f"Unsupported permission action '{action}'. "
            f"Expected one of {sorted(VALID_ACTIONS)}."
        )

    def decorator(view_function):
        @wraps(view_function)
        def wrapped_view(request, *args, **kwargs):
            require_marketplace_feature(
                request.user,
                feature_code,
                action=action,
            )
            return view_function(request, *args, **kwargs)

        return wrapped_view

    return decorator


class MarketplaceFeaturePermissionMixin:
    """Permission mixin for future class-based Marketplace views."""

    marketplace_feature_code = None
    marketplace_permission_action = "view"

    def dispatch(self, request, *args, **kwargs):
        if not self.marketplace_feature_code:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define "
                "marketplace_feature_code."
            )

        require_marketplace_feature(
            request.user,
            self.marketplace_feature_code,
            action=self.marketplace_permission_action,
        )
        return super().dispatch(request, *args, **kwargs)


def marketplace_permission_context(user):
    """UI flags; server-side views still enforce every permission."""
    checks = {
        "can_view_marketplace_dashboard": (
            MarketplaceFeatures.DASHBOARD,
            "view",
        ),
        "can_view_products": (MarketplaceFeatures.PRODUCTS, "view"),
        "can_add_product": (MarketplaceFeatures.PRODUCTS, "add"),
        "can_edit_product": (MarketplaceFeatures.PRODUCTS, "edit"),
        "can_view_orders": (MarketplaceFeatures.ORDERS, "view"),
        "can_view_sellers": (MarketplaceFeatures.SELLERS, "view"),
        "can_add_seller": (MarketplaceFeatures.SELLERS, "add"),
        "can_edit_seller": (MarketplaceFeatures.SELLERS, "edit"),
        "can_manage_commissions": (
            MarketplaceFeatures.COMMISSIONS,
            "edit",
        ),
        "can_view_settlements": (
            MarketplaceFeatures.SETTLEMENTS,
            "view",
        ),
        "can_create_settlement": (
            MarketplaceFeatures.SETTLEMENTS,
            "add",
        ),
        "can_approve_settlement": (
            MarketplaceFeatures.SETTLEMENTS,
            "approve",
        ),
        "can_view_payments": (MarketplaceFeatures.PAYMENTS, "view"),
        "can_confirm_payment": (
            MarketplaceFeatures.PAYMENTS,
            "approve",
        ),
                "can_refund_payment": (
            MarketplaceFeatures.PAYMENTS,
            "approve",
        ),

        "can_pay_settlement": (
            MarketplaceFeatures.PAYMENTS,
            "approve",
        ),
        "can_view_marketplace_reports": (
            MarketplaceFeatures.REPORTS,
            "view",
        ),
    }

    return {
        key: user_can_access_marketplace_feature(
            user,
            feature_code,
            action=action,
        )
        for key, (feature_code, action) in checks.items()
    }


marketplace_dashboard_required = marketplace_feature_required(
    MarketplaceFeatures.DASHBOARD,
    "view",
)
shop_view_required = marketplace_feature_required(
    MarketplaceFeatures.SHOP,
    "view",
)
product_view_required = marketplace_feature_required(
    MarketplaceFeatures.PRODUCTS,
    "view",
)
product_add_required = marketplace_feature_required(
    MarketplaceFeatures.PRODUCTS,
    "add",
)
product_edit_required = marketplace_feature_required(
    MarketplaceFeatures.PRODUCTS,
    "edit",
)
order_view_required = marketplace_feature_required(
    MarketplaceFeatures.ORDERS,
    "view",
)
seller_view_required = marketplace_feature_required(
    MarketplaceFeatures.SELLERS,
    "view",
)
seller_add_required = marketplace_feature_required(
    MarketplaceFeatures.SELLERS,
    "add",
)
seller_edit_required = marketplace_feature_required(
    MarketplaceFeatures.SELLERS,
    "edit",
)
commission_edit_required = marketplace_feature_required(
    MarketplaceFeatures.COMMISSIONS,
    "edit",
)
settlement_view_required = marketplace_feature_required(
    MarketplaceFeatures.SETTLEMENTS,
    "view",
)
settlement_add_required = marketplace_feature_required(
    MarketplaceFeatures.SETTLEMENTS,
    "add",
)
settlement_approve_required = marketplace_feature_required(
    MarketplaceFeatures.SETTLEMENTS,
    "approve",
)
payment_view_required = marketplace_feature_required(
    MarketplaceFeatures.PAYMENTS,
    "view",
)
payment_confirm_required = marketplace_feature_required(
    MarketplaceFeatures.PAYMENTS,
    "approve",
)
payment_refund_required = marketplace_feature_required(
    MarketplaceFeatures.PAYMENTS,
    "approve",
)

settlement_pay_required = marketplace_feature_required(
    MarketplaceFeatures.PAYMENTS,
    "approve",
)
report_view_required = marketplace_feature_required(
    MarketplaceFeatures.REPORTS,
    "view",
)