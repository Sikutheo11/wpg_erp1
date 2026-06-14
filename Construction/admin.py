from django.contrib import admin
from .models import (
    Project,
    Site,
    Task,
    ConstructionMaterial,
    ConstructionAssetUsage,
    ConstructionLabour,
    ConstructionExpense
)


# =========================
# PROJECT ADMIN
# =========================
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
        'client_name',
        'status',
        'budget',
        'get_total_spent'
    )

    list_filter = ('status', 'start_date')
    search_fields = ('name', 'code', 'client_name')
    ordering = ('-created_at',)

    def get_total_spent(self, obj):
        return obj.total_spent
    get_total_spent.short_description = "Total Spent"


# =========================
# SITE ADMIN
# =========================
@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'location', 'supervisor', 'start_date')
    search_fields = ('name', 'project__name')


# =========================
# TASK ADMIN
# =========================
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'site', 'assigned_to', 'status', 'progress')
    list_filter = ('status',)
    search_fields = ('title', 'project__name')


# =========================
# CONSTRUCTION MATERIAL ADMIN
# =========================
@admin.register(ConstructionMaterial)
class ConstructionMaterialAdmin(admin.ModelAdmin):
    list_display = ('project', 'raw_material', 'quantity_used', 'unit_cost', 'total_cost', 'date')
    list_filter = ('date',)
    search_fields = ('project__name', 'raw_material__name')


# =========================
# ASSET USAGE ADMIN
# =========================
@admin.register(ConstructionAssetUsage)
class ConstructionAssetUsageAdmin(admin.ModelAdmin):
    list_display = ('project', 'asset', 'hours_used', 'cost_per_hour', 'total_cost')
    search_fields = ('project__name', 'asset__name')


# =========================
# LABOUR ADMIN
# =========================
@admin.register(ConstructionLabour)
class ConstructionLabourAdmin(admin.ModelAdmin):
    list_display = ('project', 'employee', 'role', 'hours_worked', 'hourly_rate', 'total_cost')
    search_fields = ('project__name', 'employee__user__first_name')


# =========================
# EXPENSE ADMIN
# =========================
@admin.register(ConstructionExpense)
class ConstructionExpenseAdmin(admin.ModelAdmin):
    list_display = ('project', 'expense_type', 'amount', 'date')
    list_filter = ('expense_type', 'date')
    search_fields = ('project__name',)
