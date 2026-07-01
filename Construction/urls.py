from django.urls import path
from . import views

app_name = "Construction"


urlpatterns = [


    # ==================================================
    # DASHBOARD
    # ==================================================

    path(
        "dashboard/",
        views.construction_dashboard,
        name="construction_dashboard"
    ),



    # ==================================================
    # PROJECTS
    # ==================================================

    path(
        "projects/",
        views.project_list,
        name="project_list"
    ),


    path(
        "projects/create/",
        views.project_create,
        name="project_create"
    ),


    path(
        "projects/<int:pk>/",
        views.project_detail,
        name="project_detail"
    ),


    path(
        "projects/<int:pk>/update/",
        views.project_update,
        name="project_update"
    ),



    # ==================================================
    # SITE
    # ==================================================

    path(
        "projects/<int:project_id>/sites/create/",
        views.site_create,
        name="site_create"
    ),



    # ==================================================
    # TASK
    # ==================================================

    path(
        "projects/<int:project_id>/tasks/create/",
        views.task_create,
        name="task_create"
    ),



    # ==================================================
    # MATERIAL
    # ==================================================

    path(
        "projects/<int:project_id>/materials/create/",
        views.material_create,
        name="material_create"
    ),



    # ==================================================
    # LABOUR
    # ==================================================

    path(
        "projects/<int:project_id>/labour/create/",
        views.labour_create,
        name="labour_create"
    ),



    # ==================================================
    # ASSET USAGE
    # ==================================================

    path(
        "projects/<int:project_id>/assets/create/",
        views.asset_usage_create,
        name="asset_usage_create"
    ),



    # ==================================================
    # EXPENSE
    # ==================================================

    path(
        "projects/<int:project_id>/expenses/create/",
        views.expense_create,
        name="expense_create"
    ),


]