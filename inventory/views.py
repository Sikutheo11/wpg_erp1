from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from core.permissions import wpg_permission_required


from .models import (
    Product,
    RawMaterial,
    Asset,
    StockMovement,
    AssetAssignment
)


from .forms import (
    ProductForm,
    RawMaterialForm,
    AssetForm,
    StockMovementForm,
    AssetAssignmentForm
)


# Dashboard logic separated
from .dashboard import get_inventory_dashboard



# ==================================================
# DASHBOARD
# ==================================================

@login_required
@wpg_permission_required(
    "inventory.view_product",
    feature_code="INVENTORY_DASHBOARD",
)
def inventory_dashboard(request):

    context = get_inventory_dashboard(
        request.user
    )

    return render(
        request,
        "inventory/dashboard.html",
        context
    )



# ==================================================
# RAW MATERIALS
# ==================================================

@login_required
@wpg_permission_required(
    "inventory.view_rawmaterial",
    feature_code="INVENTORY_RAW_MATERIALS",
)
def material_list(request):

    materials = RawMaterial.objects.all()

    return render(
        request,
        "inventory/materials/material_list.html",
        {
            "materials": materials
        }
    )



@login_required
@wpg_permission_required(
    "inventory.add_rawmaterial",
    feature_code="INVENTORY_RAW_MATERIALS",
    action="add",
)
def material_create(request):

    form = RawMaterialForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Material created successfully"
        )

        return redirect(
            "inventory:material_list"
        )


    return render(
        request,
        "inventory/materials/material_form.html",
        {
            "form": form
        }
    )



@login_required
@wpg_permission_required(
    "inventory.view_rawmaterial",
    feature_code="INVENTORY_RAW_MATERIALS",
)
def material_detail(request, pk):

    material = get_object_or_404(
        RawMaterial,
        id=pk
    )


    movements = StockMovement.objects.filter(
        raw_material=material
    )


    return render(
        request,
        "inventory/materials/material_detail.html",
        {
            "material": material,
            "movements": movements
        }
    )



# ==================================================
# PRODUCTS
# ==================================================

@login_required
@wpg_permission_required(
    "inventory.view_product",
    feature_code="INVENTORY_PRODUCTS",
)
def product_list(request):

    products = Product.objects.all()

    return render(
        request,
        "inventory/products/product_list.html",
        {
            "products": products
        }
    )



@login_required
@wpg_permission_required(
    "inventory.add_product",
    feature_code="INVENTORY_PRODUCTS",
    action="add",
)
def product_create(request):

    form = ProductForm(
        request.POST or None
    )


    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Product created successfully"
        )


        return redirect(
            "inventory:product_list"
        )


    return render(
        request,
        "inventory/products/product_form.html",
        {
            "form": form
        }
    )



# ==================================================
# ASSETS
# ==================================================

@login_required
@wpg_permission_required(
    "inventory.view_asset",
    feature_code="ASSET_LIST",
)
def asset_list(request):

    assets = Asset.objects.all()


    return render(
        request,
        "inventory/assets/asset_list.html",
        {
            "assets": assets
        }
    )



@login_required
@wpg_permission_required(
    "inventory.add_asset",
    feature_code="ASSET_LIST",
    action="add",
)
def asset_create(request):

    form = AssetForm(
        request.POST or None
    )


    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Asset created successfully"
        )


        return redirect(
            "inventory:asset_list"
        )


    return render(
        request,
        "inventory/assets/asset_form.html",
        {
            "form":form
        }
    )



# ==================================================
# STOCK MOVEMENTS
# ==================================================

@login_required
@wpg_permission_required(
    "inventory.view_stockmovement",
    feature_code="INVENTORY_STOCK_MOVEMENTS",
)
def movement_list(request):

    movements = StockMovement.objects.order_by(
        "-created_at"
    )


    return render(
        request,
        "inventory/movements/movement_list.html",
        {
            "movements": movements
        }
    )



@login_required
@wpg_permission_required(
    "inventory.add_stockmovement",
    feature_code="INVENTORY_STOCK_MOVEMENTS",
    action="add",
)
def stock_create(request):

    form = StockMovementForm(
        request.POST or None
    )


    if form.is_valid():

        movement = form.save(
            commit=False
        )


        movement.created_by = request.user

        movement.save()


        messages.success(
            request,
            "Stock movement recorded"
        )


        return redirect(
            "inventory:movement_list"
        )


    return render(
        request,
        "inventory/movements/movement_form.html",
        {
            "form":form
        }
    )



# ==================================================
# REPORTS
# ==================================================

@login_required
@wpg_permission_required(
    "inventory.view_rawmaterial",
    feature_code="INVENTORY_RAW_MATERIALS",
)
def low_stock_report(request):

    materials = [
        m for m in RawMaterial.objects.all()
        if m.needs_restock
    ]


    return render(
        request,
        "inventory/reports/low_stock.html",
        {
            "materials":materials
        }
    )
