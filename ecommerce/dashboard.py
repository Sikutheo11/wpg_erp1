from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.dashboard_registry import register_dashboard

from .models import (
    EcommerceCheckout,
    EcommerceCheckoutOrder,
    MarketplaceOrderLine,
    MarketplaceSeller,
    OnlineProduct,
    SellerSettlement,
)


MONEY_FIELD = DecimalField(
    max_digits=15,
    decimal_places=2,
)

ZERO_MONEY = Decimal("0.00")

EARNED_MARKETPLACE_STATUSES = {
    "ELIGIBLE",
    "IN_SETTLEMENT",
    "SETTLED",
}

PENDING_PAYABLE_STATUSES = {
    "ELIGIBLE",
    "IN_SETTLEMENT",
}


def _money_sum(field_name, *, filter_query=None):
    """Return a reusable, null-safe monetary Sum expression."""
    options = {
        "output_field": MONEY_FIELD,
    }
    if filter_query is not None:
        options["filter"] = filter_query

    return Coalesce(
        Sum(field_name, **options),
        ZERO_MONEY,
        output_field=MONEY_FIELD,
    )


def get_ecommerce_dashboard(user=None):
    """
    Return management KPIs for WPG Ecommerce and Marketplace.

    Inventory Product remains authoritative for publication, featured status,
    business unit and price. EcommerceCheckout owns customer checkout totals.
    Enterprise Orders own payment and fulfilment. MarketplaceOrderLine owns the
    immutable seller, farm and commission snapshot used for seller accounting.
    """

    online_products = OnlineProduct.objects.select_related("product")
    checkouts = EcommerceCheckout.objects.all()
    checkout_orders = EcommerceCheckoutOrder.objects.select_related("order")
    marketplace_lines = MarketplaceOrderLine.objects.all()
    sellers = MarketplaceSeller.objects.all()
    settlements = SellerSettlement.objects.all()

    product_summary = online_products.aggregate(
        total=Count("id"),
        published=Count(
            "id",
            filter=Q(
                product__is_active=True,
                product__is_published=True,
            ),
        ),
        featured=Count(
            "id",
            filter=Q(
                product__is_active=True,
                product__is_published=True,
                product__is_featured=True,
            ),
        ),
        add_to_cart=Count(
            "id",
            filter=Q(purchase_mode="ADD_TO_CART"),
        ),
        request_quote=Count(
            "id",
            filter=Q(purchase_mode="REQUEST_QUOTE"),
        ),
        made_to_order=Count(
            "id",
            filter=Q(purchase_mode="MADE_TO_ORDER"),
        ),
        total_views=Coalesce(Sum("views"), 0),
    )

    checkout_summary = checkouts.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status="PENDING")),
        ordered=Count("id", filter=Q(status="ORDERED")),
        partial=Count("id", filter=Q(status="PARTIAL")),
        completed=Count("id", filter=Q(status="COMPLETED")),
        cancelled=Count("id", filter=Q(status="CANCELLED")),
        total_value=_money_sum("total_amount"),
    )

    order_summary = checkout_orders.aggregate(
        total=Count("id"),
        unpaid=Count(
            "id",
            filter=Q(order__payment_status="UNPAID"),
        ),
        partial=Count(
            "id",
            filter=Q(order__payment_status="PARTIAL"),
        ),
        paid=Count(
            "id",
            filter=Q(order__payment_status="PAID"),
        ),
        pending=Count(
            "id",
            filter=Q(order__status="PENDING"),
        ),
        confirmed=Count(
            "id",
            filter=Q(order__status="CONFIRMED"),
        ),
        processing=Count(
            "id",
            filter=Q(
                order__status__in={
                    "PROCESSING",
                    "IN_PRODUCTION",
                    "READY",
                }
            ),
        ),
        delivered=Count(
            "id",
            filter=Q(
                order__status__in={
                    "DELIVERED",
                    "COMPLETED",
                }
            ),
        ),
    )

    earned_filter = Q(
        settlement_status__in=EARNED_MARKETPLACE_STATUSES
    )
    pending_payable_filter = Q(
        settlement_status__in=PENDING_PAYABLE_STATUSES
    )

    marketplace_summary = marketplace_lines.aggregate(
        total_lines=Count("id"),
        earned_lines=Count("id", filter=earned_filter),
        unsettled_lines=Count(
            "id",
            filter=Q(settlement_status="UNSETTLED"),
        ),
        eligible_lines=Count(
            "id",
            filter=Q(settlement_status="ELIGIBLE"),
        ),
        in_settlement_lines=Count(
            "id",
            filter=Q(settlement_status="IN_SETTLEMENT"),
        ),
        settled_lines=Count(
            "id",
            filter=Q(settlement_status="SETTLED"),
        ),
        gross_sales=_money_sum(
            "gross_amount",
            filter_query=earned_filter,
        ),
        commission_revenue=_money_sum(
            "commission_amount",
            filter_query=earned_filter,
        ),
        seller_payable_earned=_money_sum(
            "seller_net_amount",
            filter_query=earned_filter,
        ),
        pending_seller_payable=_money_sum(
            "seller_net_amount",
            filter_query=pending_payable_filter,
        ),
        eligible_payable=_money_sum(
            "seller_net_amount",
            filter_query=Q(settlement_status="ELIGIBLE"),
        ),
        in_settlement_payable=_money_sum(
            "seller_net_amount",
            filter_query=Q(settlement_status="IN_SETTLEMENT"),
        ),
        settled_payable=_money_sum(
            "seller_net_amount",
            filter_query=Q(settlement_status="SETTLED"),
        ),
    )

    seller_summary = sellers.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        farms=Count(
            "poultry_farm_id",
            filter=Q(
                is_active=True,
                poultry_farm__isnull=False,
            ),
            distinct=True,
        ),
    )

    settlement_summary = settlements.aggregate(
        total=Count("id"),
        draft=Count("id", filter=Q(status="DRAFT")),
        approved=Count("id", filter=Q(status="APPROVED")),
        paid=Count("id", filter=Q(status="PAID")),
        cancelled=Count("id", filter=Q(status="CANCELLED")),
        draft_payable=_money_sum(
            "total_payable",
            filter_query=Q(status="DRAFT"),
        ),
        approved_payable=_money_sum(
            "total_payable",
            filter_query=Q(status="APPROVED"),
        ),
        paid_amount=_money_sum(
            "total_payable",
            filter_query=Q(status="PAID"),
        ),
    )

    business_unit_breakdown = list(
        online_products.values("product__business_unit")
        .annotate(
            total=Count("id"),
            published=Count(
                "id",
                filter=Q(
                    product__is_active=True,
                    product__is_published=True,
                ),
            ),
            featured=Count(
                "id",
                filter=Q(
                    product__is_active=True,
                    product__is_published=True,
                    product__is_featured=True,
                ),
            ),
            views=Coalesce(Sum("views"), 0),
        )
        .order_by("product__business_unit")
    )

    order_unit_breakdown = list(
        checkout_orders.values("business_unit")
        .annotate(
            orders=Count("id"),
            value=_money_sum("amount"),
        )
        .order_by("business_unit")
    )

    product_units = {
        row["product__business_unit"]: row
        for row in business_unit_breakdown
    }
    order_units = {
        row["business_unit"]: row
        for row in order_unit_breakdown
    }

    unit_definitions = (
        (
            "FURNITURE",
            "Furniture & Manufacturing",
            "Ready products, custom furniture and made-to-order production.",
            "fa-couch",
            "primary",
        ),
        (
            "CONSTRUCTION",
            "Construction & Built Environment",
            "Construction products, services and quotation-led work.",
            "fa-building",
            "warning",
        ),
        (
            "AGRICULTURE",
            "Agriculture / Poultry",
            "Eggs, livestock, poultry inputs and farm outputs.",
            "fa-egg",
            "success",
        ),
    )

    business_unit_cards = []
    for code, name, description, icon, colour in unit_definitions:
        product_row = product_units.get(code, {})
        order_row = order_units.get(code, {})
        business_unit_cards.append(
            {
                "code": code,
                "name": name,
                "description": description,
                "icon": icon,
                "colour": colour,
                "products": product_row.get("total", 0),
                "published": product_row.get("published", 0),
                "featured": product_row.get("featured", 0),
                "views": product_row.get("views", 0),
                "orders": order_row.get("orders", 0),
                "order_value": order_row.get("value", ZERO_MONEY),
            }
        )

    recent_checkouts = (
        checkouts.select_related("user")
        .prefetch_related(
            "checkout_orders",
            "checkout_orders__order",
        )
        .order_by("-created_at")[:10]
    )

    recent_settlements = (
        settlements.select_related(
            "seller",
            "seller__poultry_farm",
        )
        .order_by("-created_at", "-pk")[:5]
    )

    return {
        "products": {
            "total": product_summary["total"],
            "published": product_summary["published"],
            "featured": product_summary["featured"],
            "add_to_cart": product_summary["add_to_cart"],
            "request_quote": product_summary["request_quote"],
            "made_to_order": product_summary["made_to_order"],
        },
        "views": product_summary["total_views"],
        "featured_products": product_summary["featured"],
        "checkouts": checkout_summary,
        "orders": order_summary,
        "marketplace": marketplace_summary,
        "sellers": seller_summary,
        "settlements": settlement_summary,
        "business_units": business_unit_breakdown,
        "order_business_units": order_unit_breakdown,
        "business_unit_cards": business_unit_cards,
        "recent_checkouts": recent_checkouts,
        "recent_settlements": recent_settlements,
        "generated_at": timezone.now(),
    }


register_dashboard(
    "ecommerce",
    get_ecommerce_dashboard,
)
