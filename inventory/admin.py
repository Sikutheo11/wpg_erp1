from django.contrib import admin
from .models import (
    Category,
    Supplier,
    RawMaterial,
    Product,
    Asset,
    AssetAssignment,
    StockMovement,
    StockReservation,
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
# ========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        'product_code',
        'name',
        'category',
        'selling_price',
        'get_current_stock',
        'reorder_level',
        'is_published',
        'is_featured',
    )

    list_filter = (
        'category',
        'is_published',
        'is_featured',
    )

    search_fields = (
        'product_code',
        'name',
    )

    readonly_fields = (
        'created_at',
    )

    @admin.display(description="Current Stock")
    def get_current_stock(self, obj):
        return obj.current_stock
        get_current_stock.short_description = "Current Stock"
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

@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "product",
        "warehouse",
        "requested_quantity",
        "reserved_quantity",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "warehouse",
        "created_at",
    )

    search_fields = (
        "product__name",
        "order_item__order__order_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "reserved_at",
        "released_at",
        "completed_at",
    )