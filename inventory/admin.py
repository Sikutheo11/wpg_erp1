from django.contrib import admin
from .models import (
    Category,
    Supplier,
    RawMaterial,
    Product,
    Asset,
    AssetAssignment,
    StockMovement,
)


# =========================
# CATEGORY
# =========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


# =========================
# SUPPLIER
# =========================
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'created_at')
    search_fields = ('name', 'phone', 'email')


# =========================
# RAW MATERIAL
# =========================
@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
        'unit',
        'unit_cost',
        'current_stock',
        'needs_restock',
        'status',
    )
    list_filter = ('status',)
    search_fields = ('name', 'code', 'supplier__name')


# =========================
# PRODUCT
# =========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'product_code',
        'category',
        'selling_price',
        'current_stock',
        'material_cost',
        'estimated_profit',
    )
    list_filter = ('category',)
    search_fields = ('name', 'product_code')


# =========================
# ASSET
# =========================
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'asset_code',
        'asset_type',
        'status',
        'purchase_cost',
        'purchase_date',
    )
    list_filter = ('asset_type', 'status')
    search_fields = ('name', 'asset_code')


# =========================
# ASSET ASSIGNMENT
# =========================
@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'asset',
        'department',
        'employee',
        'assigned_date',
        'returned_date',
    )
    list_filter = ('department',)
    search_fields = ('asset__name', 'employee__first_name')


# =========================
# STOCK MOVEMENT
# =========================
@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'movement_type',
        'product',
        'raw_material',
        'quantity',
        'unit_cost',
        'created_by',
        'created_at',
    )
    list_filter = ('movement_type',)
    search_fields = (
        'product__name',
        'raw_material__name',
        'reference_no',
    )