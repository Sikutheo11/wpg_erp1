from django.urls import path

from . import views


urlpatterns = [
    # ========================================== 
    # DASHBOARD 
    # ========================================== 
    
    path( '', views.sales_dashboard, name='sales_dashboard' ),

    # ===============================
    # CUSTOMERS
    # ===============================

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



    # ===============================
    # SALES
    # ===============================

    path(
        "sales/",
        views.sale_list,
        name="sale_list"
    ),

    path(
        "sales/create/",
        views.sale_create,
        name="sale_create"
    ),

    path(
        "sales/<int:pk>/",
        views.sale_detail,
        name="sale_detail"
    ),

    path(
        "sales/<int:pk>/complete/",
        views.sale_complete,
        name="sale_complete"
    ),



    # ===============================
    # QUOTATIONS
    # ===============================

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



    # ===============================
    # INVOICES
    # ===============================

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



    # ===============================
    # PAYMENTS
    # ===============================

    path(
        "payments/create/",
        views.payment_create,
        name="payment_create"
    ),
    path(
        "invoice/<int:pk>/pdf/",
        views.invoice_pdf,
        name="invoice_pdf"
    ),

]