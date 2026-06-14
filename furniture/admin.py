from django.contrib import admin
from .models import (
    Order,
    ProductionMaterial,
    ProductionOutput,
    ProductionLabour
)


# =========================
# PRODUCTION MATERIAL INLINE
# =========================
class ProductionMaterialInline(admin.TabularInline):
    model = ProductionMaterial
    extra = 1


# =========================
# PRODUCTION OUTPUT INLINE
# =========================
class ProductionOutputInline(admin.TabularInline):
    model = ProductionOutput
    extra = 1


# =========================
# PRODUCTION LABOUR INLINE
# =========================
class ProductionLabourInline(admin.TabularInline):
    model = ProductionLabour
    extra = 1


# =========================
# PRODUCTION ORDER ADMIN
# =========================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'product',
        'quantity_to_produce',
        'status',
        'start_date',
        'end_date',
        'created_by',
        'created_at',
    )

    list_filter = ('status', 'start_date', 'end_date')
    search_fields = ('product__name',)

    inlines = [
        ProductionMaterialInline,
        ProductionOutputInline,
        ProductionLabourInline,
    ]


# =========================
# OPTIONAL: Register standalone (if needed)
# =========================
@admin.register(ProductionMaterial)
class ProductionMaterialAdmin(admin.ModelAdmin):
    list_display = ('production_order', 'raw_material', 'quantity_used', 'unit_cost')


@admin.register(ProductionOutput)
class ProductionOutputAdmin(admin.ModelAdmin):
    list_display = ('production_order', 'product', 'quantity_produced', 'date')


@admin.register(ProductionLabour)
class ProductionLabourAdmin(admin.ModelAdmin):
    list_display = ('production_order', 'employee', 'hours_worked', 'hourly_rate')

from django.contrib import admin
from .models import ProductionMachine


@admin.register(ProductionMachine)
class ProductionMachineAdmin(admin.ModelAdmin):
    list_display = (
        'asset',
        'production_order',
        'hours_used',
        'hourly_cost',
        'get_total_cost',
        'created_at'
    )

    list_filter = (
        'created_at',
        'asset',
        'production_order',
    )

    search_fields = (
        'asset__name',
        'production_order__id',
    )

    readonly_fields = ('created_at', 'get_total_cost')

    def get_total_cost(self, obj):
        return obj.total_cost

    get_total_cost.short_description = 'Total Cost'
