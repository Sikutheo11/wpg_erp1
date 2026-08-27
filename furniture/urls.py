from django.urls import include, path

from . import views


app_name = "furniture"


urlpatterns = [

    # PRE-PRODUCTION PLANNER / ESTIMATED COSTING
    path("planning/", include("furniture.planner_urls")),


    # =====================================================
    # DASHBOARD
    # =====================================================

    path(
        "dashboard/",
        views.furniture_dashboard,
        name="furniture_dashboard",
    ),

    # =====================================================
    # LEGACY FURNITURE ORDERS
    # Temporary while migrating fully to orders.Order
    # =====================================================

    path(
        "orders/",
        views.order_list,
        name="order_list",
    ),

    path(
        "orders/create/",
        views.order_create,
        name="order_create",
    ),

    path(
        "production-jobs/<int:pk>/materials/add/",
        views.add_material,
        name="add_material",
    ),

    path(
        "production-jobs/<int:pk>/labour/add/",
        views.add_labour,
        name="add_labour",
    ),

    path(
        "production-jobs/<int:pk>/machine/add/",
        views.add_machine,
        name="add_machine",
    ),

    path(
        "production-jobs/<int:pk>/output/add/",
        views.add_output,
        name="add_output",
    ),

    # =====================================================
    # ORDER ENGINE → PRODUCTION JOB
    # =====================================================

    path(
        "orders/<int:order_id>/create-production-job/",
        views.create_production_job,
        name="create_production_job",
    ),

    # =====================================================
    # PRODUCTION JOBS
    # =====================================================

    path(
        "production-jobs/",
        views.production_job_list,
        name="production_job_list",
    ),

    path(
        "production-jobs/create/",
        views.production_job_create,
        name="production_job_create",
    ),

    path(
        "production-jobs/<int:pk>/",
        views.production_job_detail,
        name="production_job_detail",
    ),

    path(
        "production-jobs/<int:pk>/kanban-move/",
        views.kanban_move_job,
        name="kanban_move_job",
    ),

    path(
        "production-jobs/<int:pk>/quotation/",
        views.create_quotation,
        name="production_job_quotation",
    ),
    # =====================================================
    # PRODUCTION TASKS
    # Only the existing task view is registered for now
    # =====================================================

    # =====================================================
    # QUOTATIONS
    # =====================================================

    path(
        "quotations/",
        views.quotation_list,
        name="quotation_list",
    ),
    path(
        "orders/<int:order_id>/production-costing/",
        views.create_order_costing,
        name="create_order_costing",
    ),

    path(
        "quotations/<int:pk>/approve/",
        views.approve_quotation,
        name="approve_quotation",
    ),

    # =====================================================
    # PRODUCTION RESOURCES
    # =====================================================

    path(
        "materials/",
        views.material_list,
        name="material_list",
    ),

    path(
        "labour/",
        views.labour_list,
        name="labour_list",
    ),

    path(
        "machines/",
        views.machine_list,
        name="machine_list",
    ),

    path(
        "outputs/",
        views.output_list,
        name="output_list",
    ),

    # =====================================================
    # REPORTS
    # =====================================================

    path(
        "reports/",
        views.production_reports,
        name="production_reports",
    ),

    # =====================================================
# PRODUCTION TASKS
# =====================================================

    path(
        "production-tasks/",
        views.production_task_list,
        name="production_task_list",
    ),

    path(
        "production-tasks/create/",
        views.production_task_create,
        name="production_task_create",
    ),

    path(
        "production-tasks/<int:pk>/",
        views.production_task_detail,
        name="production_task_detail",
    ),

    path(
        "production-tasks/<int:pk>/edit/",
        views.production_task_update,
        name="production_task_update",
    ),

    path(
        "production-tasks/<int:pk>/delete/",
        views.production_task_delete,
        name="production_task_delete",
    ),

    path(
        "production-tasks/<int:pk>/assign/",
        views.production_task_assign,
        name="production_task_assign",
    ),

    path(
        "production-tasks/<int:pk>/start/",
        views.production_task_start,
        name="production_task_start",
    ),

    path(
        "production-tasks/<int:pk>/pause/",
        views.production_task_pause,
        name="production_task_pause",
    ),

    path(
        "production-tasks/<int:pk>/resume/",
        views.production_task_resume,
        name="production_task_resume",
    ),

    path(
        "production-tasks/<int:pk>/block/",
        views.production_task_block,
        name="production_task_block",
    ),

    path(
        "production-tasks/<int:pk>/complete/",
        views.production_task_complete,
        name="production_task_complete",
    ),

    path(
        "production-tasks/<int:pk>/progress/",
        views.production_task_progress,
        name="production_task_progress",
    ),

    path(
        "production-tasks/<int:pk>/checklist/",
        views.production_task_checklist,
        name="production_task_checklist",
    ),

    path(
        "production-checklist/<int:pk>/toggle/",
        views.production_checklist_toggle,
        name="production_checklist_toggle",
    ),

    path(
        "my-production-tasks/",
        views.my_production_tasks,
        name="my_production_tasks",
    ),
    path(
        "production-jobs/<int:pk>/cost-report/",
        views.production_job_cost_report,
        name="production_job_cost_report",
    ),
    path(
        "settings/production/",
        views.production_settings,
        name="production_settings",
    ),
        # =====================================================
    # QUALITY INSPECTIONS
    # =====================================================

    path(
        "quality/",
        views.quality_inspection_list,
        name="quality_inspection_list",
    ),

    path(
        "quality/create/<int:job_pk>/",
        views.quality_inspection_create,
        name="quality_inspection_create",
    ),

    path(
        "quality/<int:pk>/",
        views.quality_inspection_detail,
        name="quality_inspection_detail",
    ),

    path(
        "quality/<int:pk>/result/",
        views.quality_inspection_result,
        name="quality_inspection_result",
    ),

    path(
        "quality/<int:pk>/approve/",
        views.quality_inspection_approve,
        name="quality_inspection_approve",
    ),

    # =====================================================
    # DEFECTS
    # =====================================================

    path(
        "defects/",
        views.production_defect_list,
        name="production_defect_list",
    ),

    path(
        "defects/<int:pk>/",
        views.production_defect_detail,
        name="production_defect_detail",
    ),

    path(
        "quality/<int:inspection_pk>/defect/",
        views.production_defect_create,
        name="production_defect_create",
    ),

    # =====================================================
    # REWORK
    # =====================================================

    path(
        "reworks/",
        views.rework_order_list,
        name="rework_order_list",
    ),

    path(
        "reworks/<int:pk>/",
        views.rework_order_detail,
        name="rework_order_detail",
    ),

    path(
        "defects/<int:defect_pk>/rework/",
        views.rework_order_create,
        name="rework_order_create",
    ),

    path(
        "reworks/<int:pk>/start/",
        views.rework_order_start,
        name="rework_order_start",
    ),

    path(
        "reworks/<int:pk>/complete/",
        views.rework_order_complete,
        name="rework_order_complete",
    ),

    path(
        "reworks/<int:pk>/verify/",
        views.rework_order_verify,
        name="rework_order_verify",
    ),
    path(
        "production-jobs/<int:pk>/schedule/",
        views.production_schedule,
        name="production_schedule",
    ),
]
