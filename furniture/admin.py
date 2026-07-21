from django.contrib import admin

from .models import (
    ProductionJob,
    BillOfMaterial,
    Quotation,
    ProductionMaterial,
    ProductionLabour,
    ProductionMachine,
    StockReservation,
    ProductionOutput,
    WorkCenter,
)

@admin.register(WorkCenter)
class WorkCenterAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "center_type",
        "capacity_per_day",
        "efficiency",
        "is_active",
    )

    list_filter = (
        "center_type",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )



# ======================================================
# ProductionJob ADMIN
# ======================================================

@admin.register(ProductionJob)
class ProductionJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product",
        "job_type",
        "quantity_to_produce",
        "status",
        "assigned_to",
        "created_at",
    )

    list_filter = (
        "job_type",
        "status",
        "created_at",
    )

    search_fields = (
        "product__name",
        "order__order_number",
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
        'production_job',
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
        'production_job',
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
        'production_job',
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
        'production_job',
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
        'production_job',
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
        'production_job',
        'product',
        'quantity_produced',
        'produced_by',
        'produced_at',
    )


    search_fields = (
        'product__name',
        'order__customer_name',
    )


    readonly_fields = (
        'produced_at',
    )

from django.contrib import admin

from .models import ProductionSettings


@admin.register(ProductionSettings)
class ProductionSettingsAdmin(admin.ModelAdmin):
    list_display = [
        "currency",
        "overhead_rate",
        "wastage_rate",
        "vat_rate",
        "target_profit_margin",
        "is_active",
        "updated_at",
    ]

    list_filter = [
        "is_active",
        "currency",
    ]

    fieldsets = (
        (
            "Costing Percentages",
            {
                "fields": (
                    "overhead_rate",
                    "wastage_rate",
                    "vat_rate",
                    "target_profit_margin",
                )
            },
        ),
        (
            "Default Costs",
            {
                "fields": (
                    "default_transport_cost",
                    "default_other_cost",
                    "default_labour_hourly_rate",
                    "default_machine_hourly_cost",
                )
            },
        ),
        (
            "General",
            {
                "fields": (
                    "currency",
                    "is_active",
                )
            },
        ),
    )

