# inventory/views.py


from django.shortcuts import (render, redirect, get_object_or_404)
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from .models import (Product, RawMaterial,Asset, StockMovement, AssetAssignment)
from .forms import (ProductForm, RawMaterialForm, AssetForm,StockMovementForm, AssetAssignmentForm)



# ==================================================
# DASHBOARD
# ==================================================

def inventory_dashboard(request):
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
    total_material_value = sum(
        m.current_stock * m.unit_cost
        for m in RawMaterial.objects.all()
    )
    recent_movements = (
        StockMovement.objects
        .select_related(
            'product',
            'raw_material',
            'created_by'
        )
        .order_by('-created_at')[:10]
    )
    context = {
        "total_products": total_products,
        "total_materials": total_materials,
        "total_assets": total_assets,
        "low_materials":low_materials,
        "low_materials_count": len(low_materials),
        "out_of_stock_count": len(out_of_stock),
        "total_inventory_value": total_material_value,
        "recent_movements": recent_movements,
    }


    return render(request,"inventory/dashboard.html", context)



# ==================================================
# RAW MATERIALS
# ==================================================

def material_list(request):
    materials = RawMaterial.objects.all()
    return render(request,"inventory/materials/material_list.html",{"materials":materials})

def material_create(request):
    form = RawMaterialForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request,"Material created successfully")
        return redirect("material_list")
    return render(request,"inventory/materials/material_form.html",{"form":form})



def material_detail(request, pk):
    material = get_object_or_404(RawMaterial, id=pk)
    movements = StockMovement.objects.filter(raw_material=material)


    return render(request,"inventory/materials/material_detail.html",
    {
            "material":material,
            "movements":movements
        }
    )



# ==================================================
# PRODUCTS
# ==================================================

def product_list(request):
    products = Product.objects.all()
    return render(request,"furniture/product_list.html",{"products":products})

def product_create(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Product created"
        )

        return redirect( "product_list")
    return render(request, "furniture/product_form.html",{"form":form})



# ==================================================
# ASSETS
# ==================================================

def asset_list(request):
    assets = Asset.objects.all()

    return render(request,"inventory/assets/asset_list.html", {"assets":assets})



def asset_create(request):
    form = AssetForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("asset_list")

    return render(request, "inventory/assets/asset_form.html",{"form":form})



# ==================================================
# STOCK MOVEMENTS
# ==================================================

def movement_list(request):
    movements = (StockMovement.objects.all().order_by("-created_at"))

    return render(request,"inventory/movements/movement_list.html",{"movements":movements})



def stock_create(request):
    form = StockMovementForm(request.POST or None)
    if form.is_valid():
        movement = form.save(commit=False)
        movement.created_by = request.user
        movement.save()
        messages.success(request, "Stock movement recorded")
        return redirect("movement_list")


    return render(request, "inventory/movements/movement_form.html",{"form":form})



# ==================================================
# REPORTS
# ==================================================

def low_stock_report(request):
    materials = [m for m in RawMaterial.objects.all()
        if m.needs_restock
    ]

    return render(request, "inventory/reports/low_stock.html",{"materials":materials})

# ==================================================
# UPDATE MATERIAL
# ==================================================

def material_update(request, pk):

    material = get_object_or_404(
        RawMaterial,
        id=pk
    )


    form = RawMaterialForm(
        request.POST or None,
        instance=material
    )


    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Material updated successfully"
        )

        return redirect(
            "material_list"
        )


    return render(
        request,
        "inventory/materials/material_form.html",
        {
            "form":form,
            "title":"Update Material"
        }
    )

def material_delete(request, pk):

    material = get_object_or_404(
        RawMaterial,
        id=pk
    )


    if request.method == "POST":

        material.delete()

        messages.success(
            request,
            "Material deleted"
        )

        return redirect(
            "material_list"
        )


    return render(
        request,
        "inventory/materials/material_delete.html",
        {
            "material":material
        }
    )


def product_update(request, pk):

    product = get_object_or_404(
        Product,
        id=pk
    )


    form = ProductForm(
        request.POST or None,
        instance=product
    )


    if form.is_valid():

        form.save()

        return redirect(
            "product_list"
        )


    return render(
        request,
        "inventory/products/product_form.html",
        {
            "form":form,
            "title":"Update Product"
        }
    )

def product_delete(request, pk):

    product = get_object_or_404(
        Product,
        id=pk
    )


    if request.method=="POST":

        product.delete()

        return redirect(
            "product_list"
        )


    return render(
        request,
        "inventory/products/product_delete.html",
        {
            "product":product
        }
    )

def asset_update(request, pk):

    asset=get_object_or_404(
        Asset,
        id=pk
    )


    form=AssetForm(
        request.POST or None,
        instance=asset
    )


    if form.is_valid():

        form.save()

        return redirect(
            "asset_list"
        )


    return render(
        request,
        "inventory/assets/asset_form.html",
        {
            "form":form
        }
    )

def asset_delete(request, pk):

    asset=get_object_or_404(
        Asset,
        id=pk
    )


    if request.method=="POST":

        asset.delete()

        return redirect(
            "asset_list"
        )


    return render(
        request,
        "inventory/assets/asset_delete.html",
        {
            "asset":asset
        }
    )

