from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from orders.models import Order

from ..models import (
    Customer,
    SalesQuotation,
)


ZERO = Decimal("0.00")


def get_sales_summary(user=None):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    quotations = SalesQuotation.objects.select_related(
        "customer",
        "converted_order",
    )

    orders = Order.objects.all()

    monthly_orders = orders.filter(
        created_at__date__range=[
            month_start,
            today,
        ]
    )

    monthly_sales = (
        monthly_orders
        .filter(
            status__in=[
                "DELIVERED",
                "COMPLETED",
            ]
        )
        .aggregate(
            total=Coalesce(
                Sum("total_amount"),
                ZERO,
            )
        )["total"]
    )

    approved_quotations = quotations.filter(
        status="approved",
    )

    open_quotations = quotations.filter(
        status__in=[
            "draft",
            "sent",
            "approved",
        ]
    )

    converted_quotations = quotations.filter(
        status="converted",
    )

    total_quotations = quotations.count()

    conversion_rate = Decimal("0.00")

    if total_quotations:
        conversion_rate = (
            Decimal(
                converted_quotations.count()
            )
            / Decimal(total_quotations)
        ) * Decimal("100")

    return {
        "total_customers": Customer.objects.filter(
            is_active=True
        ).count(),

        "total_quotations": total_quotations,

        "draft_quotations": quotations.filter(
            status="draft"
        ).count(),

        "sent_quotations": quotations.filter(
            status="sent"
        ).count(),

        "approved_quotations": (
            approved_quotations.count()
        ),

        "converted_quotations": (
            converted_quotations.count()
        ),

        "open_quotations": (
            open_quotations.count()
        ),

        "total_orders": orders.count(),

        "monthly_orders": monthly_orders.count(),

        "monthly_sales": monthly_sales,

        "conversion_rate": conversion_rate,

        "recent_quotations": (
            quotations
            .order_by(
                "-created_at"
            )[:5]
        ),

        "recent_orders": (
            orders
            .order_by(
                "-created_at"
            )[:5]
        ),
    }