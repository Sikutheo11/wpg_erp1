from django.contrib import admin
from .models import *

# =====================================================
# INLINES
# =====================================================

class BillOfMaterialInline(admin.TabularInline):
    model = BillOfMaterial
    extra = 1

# =====================================================
# CATEGORY
# =====================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


# =====================================================
# SUPPLIER
# =====================================================

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'contact_person',
        'phone',
        'email',
        'created_at'
    )

    search_fields = (
        'name',
        'contact_person',
        'phone',
    )


# =====================================================
# RAW MATERIAL
# =====================================================

@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
        'supplier',
        'unit',
        'unit_cost',
        'minimum_stock',
        'current_stock'
    )

    search_fields = (
        'name',
        'code',
    )

    list_filter = (
        'supplier',
    )


# =====================================================
# PRODUCT + BOM INLINE
# =====================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'category',
        'selling_price',
        'material_cost',
        'reorder_level',
    )

    search_fields = (
        'name',
    )

    list_filter = (
        'category',
    )

    inlines = [
        BillOfMaterialInline
    ]


# =====================================================
# BOM
# =====================================================

@admin.register(BillOfMaterial)
class BillOfMaterialAdmin(admin.ModelAdmin):

    list_display = (
        'product',
        'raw_material',
        'quantity_required'
    )

    search_fields = (
        'product__name',
        'raw_material__name'
    )
    
# =====================================================
# STOCK MOVEMENT
# =====================================================

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):

    list_display = (
        'movement_type',
        'product',
        'raw_material',
        'quantity',
        'unit_cost',
        'reference_no',
        'created_by',
        'created_at'
    )

    list_filter = (
        'movement_type',
        'created_at'
    )

    search_fields = (
        'reference_no',
        'product__name',
        'raw_material__name'
    )

    readonly_fields = (
        'created_at',
    )

    date_hierarchy = 'created_at'

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):

    list_display = (
        'asset_code',
        'name',
        'asset_type',
        'purchase_cost',
        'purchase_date',
        'status',
        'created_at',
    )

    list_filter = (
        'asset_type',
        'status',
        'purchase_date',
    )

    search_fields = (
        'asset_code',
        'name',
    )

    ordering = ('-created_at',)

    readonly_fields = ('asset_code', 'created_at')

    fieldsets = (
        ("Basic Information", {
            'fields': ('name', 'asset_type', 'asset_code')
        }),
        ("Financial Details", {
            'fields': ('purchase_cost', 'purchase_date')
        }),
        ("Status", {
            'fields': ('status',)
        }),
    )
