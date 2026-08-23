from django.contrib import admin

from .models import (
    BusinessUnit,
    EnterpriseEngine,
    Module,
    Feature,
    RoleModule,
    RoleFeature,
    DashboardCard,
    WorkflowTransition,
    ApprovalRequest,
    KPIWidget,
    AuditLog,
    Notification,
    GroupAccessProfile,
)


# ======================================================
# BUSINESS UNITS
# ======================================================

@admin.register(BusinessUnit)
class BusinessUnitAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "order",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "description",
    )

    ordering = (
        "order",
        "name",
    )


# ======================================================
# ENTERPRISE ENGINES
# ======================================================

@admin.register(EnterpriseEngine)
class EnterpriseEngineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "order",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "description",
    )

    ordering = (
        "order",
        "name",
    )


# ======================================================
# LEGACY MODULES
# ======================================================

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "url_name",
        "order",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "url_name",
    )

    ordering = (
        "order",
        "name",
    )


# ======================================================
# FEATURES
# ======================================================

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "business_unit",
        "engine",
        "url_name",
        "view_permission",
        "order",
        "is_active",
    )

    list_filter = (
        "business_unit",
        "engine",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "url_name",
        "view_permission",
        "add_permission",
        "change_permission",
        "delete_permission",
        "approve_permission",
        "business_unit__name",
        "engine__name",
    )

    ordering = (
        "order",
        "name",
    )


@admin.register(GroupAccessProfile)
class GroupAccessProfileAdmin(admin.ModelAdmin):
    list_display = (
        "group",
        "landing_feature",
        "priority",
    )
    list_select_related = (
        "group",
        "landing_feature",
    )
    search_fields = (
        "group__name",
        "landing_feature__name",
        "landing_feature__code",
    )
    ordering = (
        "priority",
        "group__name",
    )


# ======================================================
# ROLE MODULE PERMISSIONS - LEGACY
# ======================================================

@admin.register(RoleModule)
class RoleModuleAdmin(admin.ModelAdmin):
    list_display = (
        "role",
        "module",
        "can_view",
        "can_add",
        "can_edit",
        "can_delete",
        "can_approve",
    )

    list_filter = (
        "role",
        "module",
        "can_view",
        "can_approve",
    )

    search_fields = (
        "role__name",
        "module__name",
        "module__code",
    )


# ======================================================
# ROLE FEATURE PERMISSIONS
# ======================================================

@admin.register(RoleFeature)
class RoleFeatureAdmin(admin.ModelAdmin):
    list_display = (
        "role",
        "feature",
        "feature_owner",
        "can_view",
        "can_add",
        "can_edit",
        "can_delete",
        "can_approve",
    )

    list_filter = (
        "role",
        "feature__business_unit",
        "feature__engine",
        "can_view",
        "can_approve",
    )

    search_fields = (
        "role__name",
        "feature__name",
        "feature__code",
        "feature__business_unit__name",
        "feature__engine__name",
    )

    def feature_owner(self, obj):
        return obj.feature.business_unit or obj.feature.engine

    feature_owner.short_description = "Owner"


# ======================================================
# DASHBOARD CARDS
# ======================================================

@admin.register(DashboardCard)
class DashboardCardAdmin(admin.ModelAdmin):
    list_display = (
        "module",
        "title",
        "code",
        "color",
        "order",
        "is_active",
    )

    list_filter = (
        "module",
        "is_active",
    )

    search_fields = (
        "title",
        "code",
        "module__name",
    )

    ordering = (
        "module__order",
        "order",
        "title",
    )


# ======================================================
# AUDIT LOGS
# ======================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "action",
        "app_label",
        "model_name",
        "object_id",
    )

    list_filter = (
        "action",
        "app_label",
        "model_name",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__username",
        "app_label",
        "model_name",
        "object_id",
        "description",
    )

    readonly_fields = (
        "user",
        "action",
        "app_label",
        "model_name",
        "object_id",
        "description",
        "old_data",
        "new_data",
        "ip_address",
        "created_at",
    )

    ordering = (
        "-created_at",
    )


# ======================================================
# NOTIFICATIONS
# ======================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "title",
        "level",
        "is_read",
    )

    list_filter = (
        "level",
        "is_read",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__username",
        "title",
        "message",
    )

    ordering = (
        "-created_at",
    )

@admin.register(KPIWidget)
class KPIWidgetAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "code",
        "business_unit",
        "engine",
        "widget_type",
        "data_source",
        "color",
        "order",
        "is_active",
    )

    list_filter = (
        "business_unit",
        "engine",
        "widget_type",
        "is_active",
    )

    search_fields = (
        "title",
        "code",
        "data_source",
        "business_unit__name",
        "engine__name",
    )

    ordering = (
        "order",
        "title",
    )

@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "workflow_code",
        "object_app",
        "object_model",
        "object_id",
        "from_step",
        "to_step",
        "moved_by",
    )

    list_filter = (
        "workflow_code",
        "object_app",
        "object_model",
        "from_step",
        "to_step",
        "created_at",
    )

    search_fields = (
        "workflow_code",
        "object_app",
        "object_model",
        "object_id",
        "from_step",
        "to_step",
        "note",
    )

    readonly_fields = (
        "workflow_code",
        "object_app",
        "object_model",
        "object_id",
        "from_step",
        "to_step",
        "moved_by",
        "note",
        "created_at",
    )

    ordering = ("-created_at",)


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "requested_at",
        "workflow_code",
        "object_app",
        "object_model",
        "object_id",
        "from_step",
        "to_step",
        "status",
        "requested_by",
        "approved_by",
        "decided_at",
    )

    list_filter = (
        "status",
        "workflow_code",
        "object_app",
        "object_model",
        "from_step",
        "to_step",
        "requested_at",
        "decided_at",
    )

    search_fields = (
        "workflow_code",
        "object_app",
        "object_model",
        "object_id",
        "reason",
    )

    readonly_fields = (
        "workflow_code",
        "object_app",
        "object_model",
        "object_id",
        "from_step",
        "to_step",
        "requested_by",
        "approved_by",
        "status",
        "reason",
        "requested_at",
        "decided_at",
    )

    ordering = ("-requested_at",)
