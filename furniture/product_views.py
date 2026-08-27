from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from core.permissions import wpg_permission_required
from inventory.models import Product, StockMovement

from .models import BillOfMaterial, ProductionJob


@login_required
@wpg_permission_required(
    "furniture.view_productionjob",
    feature_code="FURNITURE_PRODUCTION_JOBS",
)
def furniture_product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("category"),
        pk=pk,
        business_unit="FURNITURE",
    )

    jobs = (
        ProductionJob.objects
        .filter(product=product)
        .select_related(
            "order",
            "assigned_to",
            "created_by",
        )
        .order_by("-created_at", "-pk")
    )

    active_jobs = jobs.exclude(
        status__in={
            "FINISHED_GOODS",
            "DELIVERED",
            "CLOSED",
            "CANCELLED",
        }
    )

    completed_jobs = jobs.filter(
        status__in={
            "FINISHED_GOODS",
            "DELIVERED",
            "CLOSED",
        }
    )

    bom_items = (
        BillOfMaterial.objects
        .filter(product=product)
        .select_related("raw_material")
        .order_by("raw_material__name")
    )

    bom_cost = sum(
        (
            item.total_cost
            for item in bom_items
        ),
        0,
    )

    stock_movements = (
        StockMovement.objects
        .filter(
            product=product,
            status="POSTED",
        )
        .select_related("warehouse")
        .order_by("-created_at", "-pk")[:10]
    )

    return render(
        request,
        "furniture/products/product_detail.html",
        {
            "product": product,
            "jobs": jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "bom_items": bom_items,
            "bom_cost": bom_cost,
            "stock_movements": stock_movements,
            "latest_job": jobs.first(),
        },
    )
