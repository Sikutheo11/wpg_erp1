from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from inventory.models import Product, RawMaterial
from .models import Order
from Employee.models import Employee
from Construction.models import Project


@login_required
def furniture_dashboard(request):

    # ================= PRODUCTION =================
    total_products = Product.objects.filter(
        category__name="Furniture"
    ).count()

    total_product_value = Product.objects.filter(
        category__name="Furniture"
    ).aggregate(total=Sum('selling_price'))['total'] or 0

    # ================= RAW MATERIAL =================
    total_materials = RawMaterial.objects.count()

    low_materials = RawMaterial.objects.filter(
        minimum_stock__gt=0
    ).count()

    # ================= ORDERS =================
    total_orders = Order.objects.filter(
        product__category__name="Furniture"
    ).count()

    pending_orders = Order.objects.filter(
        product__category__name="Furniture",
        status="pending"
    ).count()

    completed_orders = Order.objects.filter(
        product__category__name="Furniture",
        status="completed"
    ).count()

    # ================= WORKERS =================
    total_workers = Employee.objects.filter(
        department__name="Furniture"
    ).count()

    # ================= PROJECTS =================
    active_projects = Project.objects.filter(
        status="active"
    ).count()

    # ================= ALERTS =================
    alerts = []

    if low_materials > 0:
        alerts.append("⚠️ Low raw materials in furniture production")

    if pending_orders > 0:
        alerts.append("⏳ Pending furniture orders")

    # ================= CONTEXT =================
    context = {
        "total_products": total_products,
        "total_product_value": total_product_value,

        "total_materials": total_materials,
        "low_materials": low_materials,

        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,

        "total_workers": total_workers,
        "active_projects": active_projects,

        "alerts": alerts,
    }

    return render(request, "furniture/furniture_dashboard.html", context)