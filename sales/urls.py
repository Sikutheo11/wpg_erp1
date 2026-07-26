from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path(
        "dashboard/",
        views.sales_dashboard,
        name="sales_dashboard",
    ),

    path(
        "customers/",
        views.customer_list,
        name="customer_list",
    ),
    path(
        "customers/create/",
        views.customer_create,
        name="customer_create",
    ),
    path(
        "customers/<int:pk>/",
        views.customer_detail,
        name="customer_detail",
    ),
    path(
        "customers/<int:pk>/update/",
        views.customer_update,
        name="customer_update",
    ),
    path(
        "customers/<int:pk>/delete/",
        views.customer_delete,
        name="customer_delete",
    ),
    path(
        "customers/<int:pk>/activate/",
        views.customer_activate,
        name="customer_activate",
    ),

    path(
        "quotations/",
        views.quotation_list,
        name="quotation_list",
    ),
    path(
        "quotations/create/",
        views.quotation_create,
        name="quotation_create",
    ),
    path(
        "quotations/<int:pk>/",
        views.quotation_detail,
        name="quotation_detail",
    ),

    path(
        "quotations/<int:pk>/items/add/",
        views.quotation_item_create,
        name="quotation_item_create",
    ),
    path(
        "quotations/<int:pk>/items/<int:item_pk>/edit/",
        views.quotation_item_update,
        name="quotation_item_update",
    ),
    path(
        "quotations/<int:pk>/items/<int:item_pk>/delete/",
        views.quotation_item_delete,
        name="quotation_item_delete",
    ),

    path(
        "quotations/<int:pk>/submit/",
        views.quotation_submit,
        name="quotation_submit",
    ),
    path(
        "quotations/<int:pk>/approve/",
        views.quotation_approve,
        name="quotation_approve",
    ),
    path(
        "quotations/<int:pk>/reject/",
        views.quotation_reject,
        name="quotation_reject",
    ),
    path(
        "quotations/<int:pk>/cancel/",
        views.quotation_cancel,
        name="quotation_cancel",
    ),
    path(
        "quotations/<int:pk>/convert/",
        views.quotation_convert,
        name="quotation_convert",
    ),

    path(
        "sales/",
        views.sale_list,
        name="sale_list",
    ),
    path(
        "sales/<int:pk>/",
        views.sale_detail,
        name="sale_detail",
    ),
    path(
        "sales/<int:pk>/complete/",
        views.complete_sale_view,
        name="complete_sale",
    ),

    path(
        "invoices/",
        views.invoice_list,
        name="invoice_list",
    ),
    path(
        "invoices/<int:pk>/",
        views.invoice_detail,
        name="invoice_detail",
    ),

    path(
        "payments/",
        views.payment_list,
        name="payment_list",
    ),

    path(
        "reports/",
        views.sales_report,
        name="sales_report",
    ),
]
