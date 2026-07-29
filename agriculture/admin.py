from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AgricultureOperation,
    DailyFlockRecord,
    EggProduction,
    FeedingRecord,
    HealthRecord,
    IncubationBatch,
    MortalityRecord,
    PoultryBreed,
    PoultryFarm,
    PoultryFlock,
    PoultryHouse,
)


class AuditAdminMixin:
    readonly_fields = ("created_at", "updated_at")


class PoultryHouseInline(admin.TabularInline):
    model = PoultryHouse
    extra = 0
    fields = (
        "code",
        "name",
        "house_type",
        "capacity",
        "is_active",
    )
    show_change_link = True


class DailyFlockRecordInline(admin.TabularInline):
    model = DailyFlockRecord
    extra = 0
    fields = (
        "record_date",
        "opening_quantity",
        "additions",
        "mortality",
        "culls",
        "sold",
        "closing_quantity",
    )
    readonly_fields = ("record_date", "closing_quantity")
    ordering = ("-record_date",)
    show_change_link = True


class EggProductionInline(admin.TabularInline):
    model = EggProduction
    extra = 0
    fields = (
        "record_date",
        "eggs_collected",
        "saleable_eggs",
        "hatching_eggs",
        "cracked_eggs",
        "dirty_or_rejected_eggs",
    )
    readonly_fields = fields
    ordering = ("-record_date",)
    show_change_link = True


class FeedingRecordInline(admin.TabularInline):
    model = FeedingRecord
    extra = 0
    fields = (
        "record_date",
        "feed_product",
        "quantity_kg",
        "unit_cost",
    )
    readonly_fields = fields
    ordering = ("-record_date",)
    show_change_link = True


class HealthRecordInline(admin.TabularInline):
    model = HealthRecord
    extra = 0
    fields = (
        "record_date",
        "record_type",
        "condition_or_vaccine",
        "birds_treated",
        "next_due_date",
    )
    readonly_fields = fields
    ordering = ("-record_date",)
    show_change_link = True


class MortalityRecordInline(admin.TabularInline):
    model = MortalityRecord
    extra = 0
    fields = (
        "record_date",
        "quantity",
        "suspected_cause",
        "action_taken",
    )
    readonly_fields = fields
    ordering = ("-record_date",)
    show_change_link = True


@admin.register(PoultryFarm)
class PoultryFarmAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "location",
        "manager",
        "warehouse",
        "active_badge",
    )
    list_filter = ("is_active",)
    search_fields = (
        "code",
        "name",
        "location",
        "warehouse__name",
        "warehouse__code",
    )
    raw_id_fields = ("manager", "warehouse")
    inlines = (PoultryHouseInline,)
    ordering = ("name",)
    list_select_related = ("manager", "warehouse")

    @admin.display(description="Status", ordering="is_active")
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color:#198754;font-weight:600;">{}</span>',
                "Active",
            )

        return format_html(
            '<span style="color:#6c757d;font-weight:600;">{}</span>',
            "Inactive",
        )


@admin.register(AgricultureOperation)
class AgricultureOperationAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "operation_type",
        "farm",
        "status_badge",
        "source_order",
        "assigned_to",
        "planned_start_date",
        "budget",
        "actual_cost",
    )
    list_filter = (
        "status",
        "operation_type",
        "farm",
        "finance_posted_at",
        "created_at",
    )
    search_fields = (
        "code",
        "farm__code",
        "farm__name",
        "source_order__order_number",
        "finance_reference",
        "notes",
    )
    raw_id_fields = (
        "farm",
        "source_order",
        "assigned_to",
        "created_by",
        "approved_by",
    )
    readonly_fields = (
        "finance_reference",
        "finance_posted_at",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-pk")
    list_select_related = (
        "farm",
        "source_order",
        "assigned_to",
        "created_by",
        "approved_by",
    )
    fieldsets = (
        (
            "Operation",
            {
                "fields": (
                    "code",
                    "operation_type",
                    "farm",
                    "source_order",
                    "assigned_to",
                    "status",
                )
            },
        ),
        (
            "Schedule",
            {
                "fields": (
                    "planned_start_date",
                    "planned_end_date",
                    "actual_start_date",
                    "actual_end_date",
                )
            },
        ),
        (
            "Finance Integration",
            {
                "fields": (
                    "budget",
                    "actual_cost",
                    "finance_reference",
                    "finance_posted_at",
                )
            },
        ),
        (
            "Approval and Audit",
            {
                "fields": (
                    "created_by",
                    "approved_by",
                    "approved_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Notes",
            {
                "fields": (
                    "notes",
                    "cancellation_reason",
                )
            },
        ),
    )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        colours = {
            "DRAFT": "#6c757d",
            "PENDING": "#d39e00",
            "APPROVED": "#0d6efd",
            "ACTIVE": "#198754",
            "ON_HOLD": "#fd7e14",
            "COMPLETED": "#146c43",
            "CANCELLED": "#dc3545",
        }
        colour = colours.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>',
            colour,
            obj.get_status_display(),
        )


@admin.register(PoultryHouse)
class PoultryHouseAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "farm",
        "house_type",
        "capacity",
        "is_active",
    )
    list_filter = ("house_type", "is_active", "farm")
    search_fields = ("code", "name", "farm__code", "farm__name")
    raw_id_fields = ("farm",)
    list_select_related = ("farm",)
    ordering = ("farm__name", "code")


@admin.register(PoultryBreed)
class PoultryBreedAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "breed_type",
        "expected_laying_age_weeks",
        "expected_market_age_weeks",
        "is_active",
    )
    list_filter = ("breed_type", "is_active")
    search_fields = ("code", "name", "description")
    ordering = ("name",)


@admin.register(PoultryFlock)
class PoultryFlockAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "farm",
        "house",
        "breed",
        "purpose",
        "status_badge",
        "initial_quantity",
        "current_quantity",
        "age_weeks",
    )
    list_filter = (
        "status",
        "purpose",
        "source",
        "farm",
        "breed",
        "arrival_or_hatch_date",
    )
    search_fields = (
        "code",
        "farm__code",
        "farm__name",
        "house__code",
        "breed__name",
        "notes",
    )
    raw_id_fields = (
        "source_operation",
        "farm",
        "house",
        "breed",
        "livestock_product",
    )
    date_hierarchy = "arrival_or_hatch_date"
    ordering = ("-arrival_or_hatch_date", "-pk")
    list_select_related = (
        "source_operation",
        "farm",
        "house",
        "breed",
        "livestock_product",
    )
    inlines = (
        DailyFlockRecordInline,
        EggProductionInline,
        FeedingRecordInline,
        HealthRecordInline,
        MortalityRecordInline,
    )

    @admin.display(description="Age (weeks)")
    def age_weeks(self, obj):
        return obj.age_in_weeks

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        colours = {
            "PLANNED": "#6c757d",
            "ACTIVE": "#198754",
            "QUARANTINED": "#fd7e14",
            "SOLD": "#0d6efd",
            "CLOSED": "#212529",
            "CANCELLED": "#dc3545",
        }
        colour = colours.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>',
            colour,
            obj.get_status_display(),
        )


@admin.register(DailyFlockRecord)
class DailyFlockRecordAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "record_date",
        "flock",
        "opening_quantity",
        "additions",
        "mortality",
        "culls",
        "sold",
        "closing_quantity",
        "recorded_by",
    )
    list_filter = ("record_date", "flock__farm")
    search_fields = (
        "flock__code",
        "operation__code",
        "notes",
    )
    raw_id_fields = ("operation", "flock", "recorded_by")
    date_hierarchy = "record_date"
    ordering = ("-record_date", "-pk")
    list_select_related = ("operation", "flock", "recorded_by")


@admin.register(EggProduction)
class EggProductionAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "record_date",
        "flock",
        "eggs_collected",
        "saleable_eggs",
        "hatching_eggs",
        "cracked_eggs",
        "laying_rate_display",
        "warehouse",
        "inventory_posted",
    )
    list_filter = (
        "record_date",
        "flock__farm",
        "warehouse",
        "stock_movement",
    )
    search_fields = (
        "flock__code",
        "operation__code",
        "inventory_product__name",
        "notes",
    )
    raw_id_fields = (
        "operation",
        "flock",
        "inventory_product",
        "warehouse",
        "stock_movement",
        "recorded_by",
    )
    readonly_fields = ("stock_movement", "created_at", "updated_at")
    date_hierarchy = "record_date"
    ordering = ("-record_date", "-pk")
    list_select_related = (
        "operation",
        "flock",
        "inventory_product",
        "warehouse",
        "stock_movement",
        "recorded_by",
    )

    @admin.display(description="Laying rate")
    def laying_rate_display(self, obj):
        return f"{obj.laying_rate}%"

    @admin.display(description="Inventory", boolean=True)
    def inventory_posted(self, obj):
        return bool(obj.stock_movement_id)


@admin.register(IncubationBatch)
class IncubationBatchAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "source_flock",
        "eggs_set",
        "set_date",
        "expected_hatch_date",
        "status_badge",
        "chicks_hatched",
        "hatchability_display",
        "inventory_posted",
    )
    list_filter = (
        "status",
        "set_date",
        "expected_hatch_date",
        "output_warehouse",
    )
    search_fields = (
        "code",
        "operation__code",
        "source_flock__code",
        "notes",
    )
    raw_id_fields = (
        "operation",
        "source_flock",
        "incubator_asset",
        "chick_product",
        "output_warehouse",
        "stock_movement",
    )
    readonly_fields = ("stock_movement", "created_at", "updated_at")
    date_hierarchy = "set_date"
    ordering = ("-set_date", "-pk")
    list_select_related = (
        "operation",
        "source_flock",
        "incubator_asset",
        "chick_product",
        "output_warehouse",
        "stock_movement",
    )

    @admin.display(description="Hatchability")
    def hatchability_display(self, obj):
        return f"{obj.hatchability_rate}%"

    @admin.display(description="Inventory", boolean=True)
    def inventory_posted(self, obj):
        return bool(obj.stock_movement_id)

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        colours = {
            "PLANNED": "#6c757d",
            "SET": "#0d6efd",
            "CANDLED": "#6f42c1",
            "HATCHING": "#fd7e14",
            "COMPLETED": "#198754",
            "CANCELLED": "#dc3545",
        }
        colour = colours.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>',
            colour,
            obj.get_status_display(),
        )


@admin.register(FeedingRecord)
class FeedingRecordAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "record_date",
        "flock",
        "feed_product",
        "quantity_kg",
        "unit_cost",
        "total_cost_display",
        "warehouse",
        "inventory_posted",
    )
    list_filter = ("record_date", "flock__farm", "warehouse")
    search_fields = (
        "flock__code",
        "operation__code",
        "feed_product__name",
        "notes",
    )
    raw_id_fields = (
        "operation",
        "flock",
        "feed_product",
        "warehouse",
        "stock_movement",
        "recorded_by",
    )
    readonly_fields = ("stock_movement", "created_at", "updated_at")
    date_hierarchy = "record_date"
    ordering = ("-record_date", "-pk")
    list_select_related = (
        "operation",
        "flock",
        "feed_product",
        "warehouse",
        "stock_movement",
        "recorded_by",
    )

    @admin.display(description="Total cost")
    def total_cost_display(self, obj):
        return f"{obj.total_cost:,.2f}"

    @admin.display(description="Inventory", boolean=True)
    def inventory_posted(self, obj):
        return bool(obj.stock_movement_id)


@admin.register(HealthRecord)
class HealthRecordAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "record_date",
        "flock",
        "record_type",
        "condition_or_vaccine",
        "birds_treated",
        "next_due_date",
        "cost",
    )
    list_filter = (
        "record_type",
        "record_date",
        "next_due_date",
        "flock__farm",
    )
    search_fields = (
        "flock__code",
        "operation__code",
        "condition_or_vaccine",
        "veterinarian_or_provider",
        "notes",
    )
    raw_id_fields = (
        "operation",
        "flock",
        "medicine_product",
        "recorded_by",
    )
    date_hierarchy = "record_date"
    ordering = ("-record_date", "-pk")
    list_select_related = (
        "operation",
        "flock",
        "medicine_product",
        "recorded_by",
    )


@admin.register(MortalityRecord)
class MortalityRecordAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "record_date",
        "flock",
        "quantity",
        "suspected_cause",
        "health_record",
        "recorded_by",
    )
    list_filter = (
        "suspected_cause",
        "record_date",
        "flock__farm",
    )
    search_fields = (
        "flock__code",
        "operation__code",
        "action_taken",
        "notes",
    )
    raw_id_fields = (
        "operation",
        "flock",
        "health_record",
        "recorded_by",
    )
    date_hierarchy = "record_date"
    ordering = ("-record_date", "-pk")
    list_select_related = (
        "operation",
        "flock",
        "health_record",
        "recorded_by",
    )
