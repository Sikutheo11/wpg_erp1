from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

from core.permissions import wpg_permission_required


from .models import (
    Category,
    Warehouse,
    Supplier,
    Product,
    RawMaterial,
    Asset,
    StockMovement,
    AssetAssignment
)


from .forms import (
    CategoryForm,
    ProductForm,
    RawMaterialForm,
    AssetForm,
    StockMovementForm,
    AssetAssignmentForm,
    SupplierForm,
    WarehouseForm,
)


# Dashboard logic separated
from .dashboard import get_inventory_dashboard
from .services import StockService



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
# MASTER DATA
# ==================================================

@login_required
@wpg_permission_required("inventory.view_category", feature_code="INVENTORY_CATEGORIES")
def category_list(request):
    return render(
        request,
        "inventory/master_data/category_list.html",
        {"categories": Category.objects.order_by("name")},
    )


@login_required
@wpg_permission_required(
    "inventory.add_category",
    feature_code="INVENTORY_CATEGORIES",
    action="add",
)
def category_create(request):
    form = CategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Category created successfully.")
        return redirect("inventory:category_list")
    return render(
        request,
        "inventory/master_data/master_data_form.html",
        {"form": form, "title": "Add Category", "cancel_url": "inventory:category_list"},
    )


@login_required
@wpg_permission_required(
    "inventory.change_category",
    feature_code="INVENTORY_CATEGORIES",
    action="edit",
)
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if form.is_valid():
        form.save()
        messages.success(request, "Category updated successfully.")
        return redirect("inventory:category_list")
    return render(
        request,
        "inventory/master_data/master_data_form.html",
        {"form": form, "title": "Edit Category", "cancel_url": "inventory:category_list"},
    )


@login_required
@wpg_permission_required("inventory.view_warehouse", feature_code="INVENTORY_WAREHOUSES")
def warehouse_list(request):
    return render(
        request,
        "inventory/master_data/warehouse_list.html",
        {
            "warehouses": Warehouse.objects.select_related(
                "manager", "manager__user"
            ).order_by("warehouse_type", "name")
        },
    )


@login_required
@wpg_permission_required(
    "inventory.add_warehouse",
    feature_code="INVENTORY_WAREHOUSES",
    action="add",
)
def warehouse_create(request):
    form = WarehouseForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Warehouse created successfully.")
        return redirect("inventory:warehouse_list")
    return render(
        request,
        "inventory/master_data/master_data_form.html",
        {"form": form, "title": "Add Warehouse", "cancel_url": "inventory:warehouse_list"},
    )


@login_required
@wpg_permission_required(
    "inventory.change_warehouse",
    feature_code="INVENTORY_WAREHOUSES",
    action="edit",
)
def warehouse_update(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    form = WarehouseForm(request.POST or None, instance=warehouse)
    if form.is_valid():
        form.save()
        messages.success(request, "Warehouse updated successfully.")
        return redirect("inventory:warehouse_list")
    return render(
        request,
        "inventory/master_data/master_data_form.html",
        {"form": form, "title": "Edit Warehouse", "cancel_url": "inventory:warehouse_list"},
    )


@login_required
@wpg_permission_required("inventory.view_supplier", feature_code="INVENTORY_SUPPLIERS")
def supplier_list(request):
    return render(
        request,
        "inventory/master_data/supplier_list.html",
        {"suppliers": Supplier.objects.order_by("name")},
    )


@login_required
@wpg_permission_required(
    "inventory.add_supplier",
    feature_code="INVENTORY_SUPPLIERS",
    action="add",
)
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Supplier created successfully.")
        return redirect("inventory:supplier_list")
    return render(
        request,
        "inventory/master_data/master_data_form.html",
        {"form": form, "title": "Add Supplier", "cancel_url": "inventory:supplier_list"},
    )


@login_required
@wpg_permission_required(
    "inventory.change_supplier",
    feature_code="INVENTORY_SUPPLIERS",
    action="edit",
)
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(request.POST or None, instance=supplier)
    if form.is_valid():
        form.save()
        messages.success(request, "Supplier updated successfully.")
        return redirect("inventory:supplier_list")
    return render(
        request,
        "inventory/master_data/master_data_form.html",
        {"form": form, "title": "Edit Supplier", "cancel_url": "inventory:supplier_list"},
    )


@login_required
@wpg_permission_required("inventory.view_assetassignment", feature_code="ASSET_ASSIGNMENTS")
def asset_assignment_list(request):
    assignments = AssetAssignment.objects.select_related(
        "asset", "department", "employee", "employee__user"
    ).order_by("-assigned_date", "-pk")
    return render(
        request,
        "inventory/assets/asset_assignment_list.html",
        {"assignments": assignments},
    )


@login_required
@wpg_permission_required(
    "inventory.add_assetassignment",
    feature_code="ASSET_ASSIGNMENTS",
    action="add",
)
def asset_assignment_create(request):
    form = AssetAssignmentForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Asset assignment created successfully.")
        return redirect("inventory:asset_assignment_list")
    return render(
        request,
        "inventory/assets/asset_assignment_form.html",
        {"form": form, "title": "Assign Asset"},
    )


@login_required
@wpg_permission_required(
    "inventory.change_assetassignment",
    feature_code="ASSET_ASSIGNMENTS",
    action="edit",
)
def asset_assignment_update(request, pk):
    assignment = get_object_or_404(AssetAssignment, pk=pk)
    form = AssetAssignmentForm(request.POST or None, instance=assignment)
    if form.is_valid():
        form.save()
        messages.success(request, "Asset assignment updated successfully.")
        return redirect("inventory:asset_assignment_list")
    return render(
        request,
        "inventory/assets/asset_assignment_form.html",
        {"form": form, "title": "Edit Asset Assignment"},
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
    form = RawMaterialForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Material created successfully")
        return redirect("inventory:material_list")
    return render(
        request,
        "inventory/materials/material_form.html",
        {"form": form, "material": None},
    )


@login_required
@wpg_permission_required(
    "inventory.change_rawmaterial",
    feature_code="INVENTORY_RAW_MATERIALS",
    action="edit",
)
def material_update(request, pk):
    material = get_object_or_404(RawMaterial, pk=pk)
    form = RawMaterialForm(request.POST or None, instance=material)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Material updated successfully.")
        return redirect("inventory:material_list")
    return render(
        request,
        "inventory/materials/material_form.html",
        {"form": form, "material": material},
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
        request.POST or None,
        request.FILES or None,
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
            "form": form,
            "product": None,
        }
    )


@login_required
@wpg_permission_required(
    "inventory.change_product",
    feature_code="INVENTORY_PRODUCTS",
    action="edit",
)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product updated successfully.")
        return redirect("inventory:product_list")
    return render(
        request,
        "inventory/products/product_form.html",
        {"form": form, "product": product},
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
            "form":form,
            "asset": None,
        }
    )


@login_required
@wpg_permission_required(
    "inventory.change_asset",
    feature_code="ASSET_LIST",
    action="edit",
)
def asset_update(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    form = AssetForm(request.POST or None, instance=asset)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Asset updated successfully.")
        return redirect("inventory:asset_list")
    return render(
        request,
        "inventory/assets/asset_form.html",
        {"form": form, "asset": asset},
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
    movements = StockMovement.objects.select_related(
        "product", "warehouse", "created_by"
    ).order_by("-created_at")


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
    form = StockMovementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        movement_type = data["movement_type"]
        common = {
            "product": data["product"],
            "warehouse": data["warehouse"],
            "quantity": data["quantity"],
            "unit_cost": data.get("unit_cost") or None,
            "business_unit": data["product"].business_unit,
            "reference_type": data["reference_type"],
            "reference_no": data.get("reference_no", ""),
            "notes": data.get("notes", ""),
            "actor": request.user,
        }
        try:
            if movement_type in {"IN", "RETURN_IN"}:
                StockService.receive_stock(
                    **common,
                    movement_type=movement_type,
                )
            elif movement_type in {"OUT", "RETURN_OUT"}:
                StockService.issue_stock(
                    **common,
                    movement_type=movement_type,
                )
            else:
                StockService.adjust_stock(
                    **common,
                    direction="IN" if movement_type == "ADJUSTMENT_IN" else "OUT",
                )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Stock movement recorded successfully.")
            return redirect("inventory:movement_list")


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
