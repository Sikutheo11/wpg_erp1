# sales/urls.py


from django.urls import path

from . import views



app_name = "sales"



urlpatterns = [


    # =====================================================
    # DASHBOARD
    # =====================================================

    path(
        "dashboard/",
        views.sales_dashboard,
        name="sales_dashboard"
    ),



    # =====================================================
    # CUSTOMER MANAGEMENT
    # =====================================================


    path(
        "customers/",
        views.customer_list,
        name="customer_list"
    ),


    path(
        "customers/create/",
        views.customer_create,
        name="customer_create"
    ),


    path(
        "customers/<int:pk>/",
        views.customer_detail,
        name="customer_detail"
    ),


    path(
        "customers/<int:pk>/update/",
        views.customer_update,
        name="customer_update"
    ),


    path(
        "customers/<int:pk>/delete/",
        views.customer_delete,
        name="customer_delete"
    ),




    # =====================================================
    # SALES QUOTATION
    # =====================================================


    path(
        "quotations/",
        views.quotation_list,
        name="quotation_list"
    ),


    path(
        "quotations/create/",
        views.quotation_create,
        name="quotation_create"
    ),


    path(
        "quotations/<int:pk>/",
        views.quotation_detail,
        name="quotation_detail"
    ),




    # =====================================================
    # SALES
    # =====================================================


    path(
        "sales/",
        views.sale_list,
        name="sale_list"
    ),


    path(
        "sales/<int:pk>/",
        views.sale_detail,
        name="sale_detail"
    ),


    path(
        "sales/<int:pk>/complete/",
        views.complete_sale_view,
        name="complete_sale"
    ),




    # =====================================================
    # INVOICES
    # =====================================================


    path(
        "invoices/",
        views.invoice_list,
        name="invoice_list"
    ),


    path(
        "invoices/<int:pk>/",
        views.invoice_detail,
        name="invoice_detail"
    ),




    # =====================================================
    # CUSTOMER PAYMENTS
    # =====================================================


    path(
        "payments/",
        views.payment_list,
        name="payment_list"
    ),




    # =====================================================
    # REPORTS
    # =====================================================


    path(
        "reports/",
        views.sales_report,
        name="sales_report"
    ),


]