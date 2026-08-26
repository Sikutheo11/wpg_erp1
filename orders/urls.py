from django.urls import path
from . import views
app_name = "orders"

urlpatterns = [

    # ======================================================
    # ORDERS
    # ======================================================

    path(
        "",
        views.order_catalog,
        name="order_list",
    ),

    path("all/", views.order_list, name="all_orders"),

    path(
        "type/<str:business_unit>/<str:order_type>/",
        views.order_list,
        name="order_type_orders",
    ),

    path(
        "create/",
        views.business_unit_select,
        name="business_unit_select",
    ),

    path(
        "create/type/",
        views.order_type_select,
        name="order_type_select",
    ),

    path(
        "create/form/",
        views.order_create,
        name="order_create",
    ),

    path(
        "<int:pk>/",
        views.order_detail,
        name="order_detail",
    ),

    # ======================================================
    # ORDER ITEMS
    # ======================================================

    path(
        "<int:pk>/items/add/",
        views.add_order_item,
        name="add_order_item",
    ),

    path(
        "items/<int:pk>/edit/",
        views.edit_order_item,
        name="edit_order_item",
    ),

    path(
        "items/<int:pk>/remove/",
        views.remove_order_item,
        name="remove_order_item",
    ),

    # ======================================================
    # ORDER WORKFLOW
    # ======================================================

    path(
        "<int:pk>/submit/",
        views.submit_order,
        name="submit_order",
    ),

    path(
        "<int:pk>/confirm/",
        views.confirm_order,
        name="confirm_order",
    ),

    path(
        "<int:pk>/cancel/",
        views.cancel_order,
        name="cancel_order",
    ),

    # ======================================================
    # DELIVERY WORKFLOW
    # ======================================================
    path(
        "<int:pk>/processing/",
        views.mark_processing,
        name="mark_processing",
    ),
    
    
    path(
        "<int:pk>/ready/",
        views.mark_ready,
        name="mark_ready",
    ),
   
    path(
        "<int:pk>/shipped/",
        views.mark_shipped,
        name="mark_shipped",
    ),

    path(
        "<int:pk>/dispatch/",
        views.order_dispatch,
        name="order_dispatch",
    ),

    path(
        "<int:pk>/deliver/",
        views.deliver_order,
        name="deliver_order",
    ),

    path(
        "<int:pk>/delivery/cancel/",
        views.cancel_delivery,
        name="cancel_delivery",
    ),

    path(
        "<int:pk>/processing/",
        views.mark_processing,
        name="mark_processing",
    ),

    # ======================================================
    # INVENTORY
    # ======================================================

    # path(
    #     "<int:pk>/reserve/",
    #     views.reserve_order,
    #     name="reserve_order",
    # ),

    # path(
    #     "<int:pk>/fulfil/",
    #     views.fulfil_order,
    #     name="fulfil_order",
    # ),

    # path(
    #     "<int:pk>/release/",
    #     views.release_order,
    #     name="release_order",
    # ),

]
