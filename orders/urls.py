from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [

    # ===========================
    # ORDERS
    # ===========================

    path(
        "",
        views.order_list,
        name="order_list",
    ),

    path(
        "<int:order_id>/",
        views.order_detail,
        name="order_detail",
    ),

    path(
        "<int:order_id>/status/",
        views.update_order_status,
        name="update_status",
    ),

    # ===========================
    # RESTOCK
    # ===========================

    path(
        "restock/create/",
        views.restock_order_create,
        name="restock_order_create",
    ),

    # ===========================
    # CREATE PRODUCTION JOB
    # ===========================

    path(
        "<int:order_id>/production/",
        views.create_production_job,
        name="create_production_job",
    ),

]