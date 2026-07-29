from django.contrib import admin

from .models import (
    Asset,
    AssetAssignment,
    Category,
    Product,
    RawMaterial,
    StockMovement,
    StockReservation,
    Supplier,
    Warehouse,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "warehouse_type",
        "business_unit",
        "manager",
        "is_active",
        "allow_negative_stock",
    )
    list_filter = (
        "warehouse_type",
        "business_unit",
        "is_active",
        "allow_negative_stock",
    )
    search_fields = (
        "code",
        "name",
        "location",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("warehouse_type", "name")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "contact_person",
        "phone",
        "email",
        "tax_number",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "contact_person",
        "phone",
        "email",
        "tax_number",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "supplier",
        "status",
        "unit",
        "unit_cost",
        "current_stock",
        "needs_restock",
    )
    list_filter = ("status", "category", "supplier")
    search_fields = ("code", "name", "linked_product__product_code")
    autocomplete_fields = ("supplier", "category", "linked_product")
    readonly_fields = ("created_at", "updated_at", "current_stock")
    ordering = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "product_code",
        "name",
        "product_type",
        "business_unit",
        "category",
        "unit",
        "selling_price",
        "standard_cost",
        "track_inventory",
        "is_active",
        "is_published",
    )
    list_filter = (
        "product_type",
        "business_unit",
        "category",
        "valuation_method",
        "track_inventory",
        "is_active",
        "is_published",
        "is_featured",
    )
    search_fields = (
        "product_code",
        "barcode",
        "name",
        "description",
        "slug",
    )
    autocomplete_fields = ("category", "preferred_supplier")
    readonly_fields = ("created_at", "updated_at", "current_stock")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("business_unit", "name")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "asset_code",
        "name",
        "asset_type",
        "purchase_cost",
        "purchase_date",
        "status",
    )
    list_filter = ("asset_type", "status", "purchase_date")
    search_fields = ("asset_code", "name")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "purchase_date"


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "department",
        "employee",
        "assigned_date",
        "returned_date",
    )
    list_filter = ("department", "assigned_date", "returned_date")
    search_fields = ("asset__asset_code", "asset__name")
    autocomplete_fields = ("asset",)
    date_hierarchy = "assigned_date"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "stock_item",
        "warehouse",
        "movement_type",
        "status",
        "quantity",
        "unit_cost",
        "total_cost",
        "business_unit",
        "reference_type",
        "reference_no",
        "created_at",
    )
    list_filter = (
        "movement_type",
        "status",
        "business_unit",
        "reference_type",
        "warehouse",
        "created_at",
    )
    search_fields = (
        "product__product_code",
        "product__name",
        "raw_material__code",
        "raw_material__name",
        "reference_id",
        "reference_no",
        "notes",
    )
    autocomplete_fields = (
        "product",
        "raw_material",
        "warehouse",
        "reversal_of",
    )
    readonly_fields = ("created_at", "updated_at", "total_cost")
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-pk")

    @admin.display(description="Stock item", ordering="product__name")
    def stock_item(self, obj):
        return obj.product or obj.raw_material


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_item",
        "product",
        "warehouse",
        "requested_quantity",
        "reserved_quantity",
        "completed_quantity",
        "shortage_quantity",
        "status",
        "reserved_at",
    )
    list_filter = ("status", "warehouse", "reserved_at", "created_at")
    search_fields = (
        "product__product_code",
        "product__name",
        "order_item__order__order_number",
        "note",
    )
    autocomplete_fields = (
        "product",
        "warehouse",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "shortage_quantity",
        "remaining_reserved_quantity",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
