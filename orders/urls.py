from django.urls import path

from . import views


app_name = "orders"


urlpatterns = [
    path(
        "",
        views.order_list,
        name="order_list",
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
    path(
        "<int:pk>/deliver/",
        views.deliver_order,
        name="deliver_order",
    ),
    path(
        "<int:pk>/ship/",
        views.mark_shipped,
        name="mark_shipped",
    ),

    path(
        "<int:pk>/deliver/",
        views.deliver_order,
        name="deliver_order",
    ),
]