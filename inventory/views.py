from django.shortcuts import render
from django.db.models import Sum, F

from inventory.models import (
    Product,
    RawMaterial,
    StockMovement
)


def inventory_dashboard(request):

    total_products = Product.objects.count()

    total_materials = RawMaterial.objects.count()

    low_materials = [
        material for material in RawMaterial.objects.all()
        if material.current_stock <= material.minimum_stock
    ]

    out_of_stock = [
        material for material in RawMaterial.objects.all()
        if material.current_stock <= 0
    ]

    total_stock_value = sum(
        material.current_stock * material.unit_cost
        for material in RawMaterial.objects.all()
    )

    recent_movements = StockMovement.objects.order_by('-created_at')[:10]

    context = {
        'total_products': total_products,
        'total_materials': total_materials,
        'low_materials_count': len(low_materials),
        'out_of_stock_count': len(out_of_stock),
        'total_stock_value': total_stock_value,
        'low_materials': low_materials,
        'recent_movements': recent_movements,
    }

    return render(
        request,
        'inventory/dashboard.html',
        context
    )