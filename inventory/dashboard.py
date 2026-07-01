from .models import Product, RawMaterial, Asset, StockMovement

def get_inventory_dashboard(user):
    total_products = Product.objects.count()
    total_materials = RawMaterial.objects.count()
    total_assets = Asset.objects.count()
    low_materials = [
        m for m in RawMaterial.objects.all()
        if m.needs_restock
    ]
    out_of_stock = [
        m for m in RawMaterial.objects.all()
        if m.current_stock <= 0
    ]
    inventory_value = sum(
        m.current_stock * m.unit_cost
        for m in RawMaterial.objects.all()
    )
    recent_movements = (
        StockMovement.objects
        .select_related(
            "product",
            "raw_material",
            "created_by"
        )
        .order_by("-created_at")[:10]
    )


    return {

        "total_products": total_products,
        "total_materials": total_materials,
        "total_assets":  total_assets,
        "low_materials": low_materials,
        "low_materials_count": len(low_materials),
        "out_of_stock_count":len(out_of_stock),
        "total_inventory_value":inventory_value,
        "recent_movements":recent_movements,

    }