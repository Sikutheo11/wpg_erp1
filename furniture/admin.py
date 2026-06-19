from django.contrib import admin

from .models import (
    Order,
    BillOfMaterial,
    Quotation,
    ProductionMaterial,
    ProductionLabour,
    ProductionMachine,
    StockReservation,
    ProductionOutput,
)



# ======================================================
# ORDER ADMIN
# ======================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'customer_name',
        'product',
        'quantity_to_produce',
        'assigned_to',
        'status',
        'created_at',
    )


    list_filter = (
        'status',
        'created_at',
        'assigned_to',
    )


    search_fields = (
        'customer_name',
        'product__name',
    )


    readonly_fields = (
        'created_at',
    )



# ======================================================
# BOM ADMIN
# ======================================================

@admin.register(BillOfMaterial)
class BillOfMaterialAdmin(admin.ModelAdmin):


    list_display = (
        'product',
        'raw_material',
        'quantity_required',
        'total_cost',
    )


    search_fields = (
        'product__name',
        'raw_material__name',
    )



# ======================================================
# QUOTATION ADMIN
# ======================================================

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):


    list_display = (
        'order',
        'prepared_by',
        'approved_by',
        'selling_price',
        'status',
        'created_at',
    )


    list_filter = (
        'status',
        'created_at',
    )


    search_fields = (
        'order__customer_name',
        'order__product__name',
    )


    readonly_fields = (
        'created_at',
    )



# ======================================================
# MATERIAL CONSUMPTION ADMIN
# ======================================================

@admin.register(ProductionMaterial)
class ProductionMaterialAdmin(admin.ModelAdmin):


    list_display = (
        'order',
        'raw_material',
        'quantity_used',
        'unit_cost',
        'total_cost',
    )


    search_fields = (
        'order__customer_name',
        'raw_material__name',
    )



# ======================================================
# LABOUR COST ADMIN
# ======================================================

@admin.register(ProductionLabour)
class ProductionLabourAdmin(admin.ModelAdmin):


    list_display = (
        'order',
        'employee',
        'hours_worked',
        'hourly_rate',
        'total_cost',
    )


    search_fields = (
        'employee__user__username',
        'order__customer_name',
    )



# ======================================================
# MACHINE COST ADMIN
# ======================================================

@admin.register(ProductionMachine)
class ProductionMachineAdmin(admin.ModelAdmin):


    list_display = (
        'order',
        'asset',
        'hours_used',
        'hourly_cost',
        'total_cost',
    )


    search_fields = (
        'asset__name',
        'order__customer_name',
    )



# ======================================================
# STOCK RESERVATION ADMIN
# ======================================================

@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):


    list_display = (
        'order',
        'raw_material',
        'quantity',
        'status',
    )


    list_filter = (
        'status',
    )


    search_fields = (
        'raw_material__name',
        'order__customer_name',
    )



# ======================================================
# PRODUCTION OUTPUT ADMIN
# ======================================================

@admin.register(ProductionOutput)
class ProductionOutputAdmin(admin.ModelAdmin):


    list_display = (
        'order',
        'product',
        'quantity_produced',
        'produced_by',
        'date',
    )


    search_fields = (
        'product__name',
        'order__customer_name',
    )


    readonly_fields = (
        'date',
    )