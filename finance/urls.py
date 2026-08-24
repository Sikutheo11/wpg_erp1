from django.urls import path
from . import views
app_name = "finance"


urlpatterns = [
    path("catalog/groups/new/", views.obligation_item_group_create, name="obligation_item_group_create"),
    path("catalog/items/new/", views.obligation_item_type_create, name="obligation_item_type_create"),
    path("catalog/groups.json", views.obligation_item_groups_json, name="obligation_item_groups_json"),
    path("catalog/items.json", views.obligation_item_types_json, name="obligation_item_types_json"),

    # =====================================================
    # FINANCE DASHBOARD
    # =====================================================

    path(
        '',
        views.finance_dashboard,
        name='dashboard'
    ),


    path(
        'dashboard/',
        views.finance_dashboard,
        name='finance_dashboard'
    ),



    # =====================================================
    # ACCOUNTS
    # =====================================================

    path(
        'accounts/',
        views.account_list,
        name='account_list'
    ),
    path(
        'accounts/create/',
        views.account_create,
        name='account_create'
    ),
    path(
        'accounts/<int:pk>/edit/',
        views.account_update,
        name='account_update'
    ),
    path(
        'accounts/<int:pk>/delete/',
        views.account_delete,
        name='account_delete'
    ),



    # =====================================================
    # INCOME
    # =====================================================

    path(
        'income/',
        views.income_list,
        name='income_list'
    ),
    path(
        'income/create/',
        views.income_create,
        name='income_create'
    ),




    # =====================================================
    # EXPENSE
    # =====================================================

    path(
        'expenses/',
        views.expense_list,
        name='expense_list'
    ),
    path(
        'expenses/create/',
        views.expense_create,
        name='expense_create'
    ),




    # =====================================================
    # RECEIVABLE
    # =====================================================

    path(
        'receivables/',
        views.receivable_list,
        name='receivable_list'
    ),





    # =====================================================
    # PAYABLE
    # =====================================================

    path(
        'payables/',
        views.payable_list,
        name='payable_list'
    ),

    path(
        "payables/create/",
        views.payable_create,
        name="payable_create",
    ),

    path(
        "payables/<int:pk>/",
        views.payable_detail,
        name="payable_detail",
    ),

    path(
        "payables/<int:pk>/payment/",
        views.payable_payment,
        name="payable_payment",
    ),





    # =====================================================
    # PAYMENTS
    # =====================================================

    path(
        'payments/',
        views.payment_list,
        name='payment_list'
    ),





    # =====================================================
    # PAYROLL
    # =====================================================

    path(
        'payroll/',
        views.payroll_list,
        name='payroll_list'
    ),





    # =====================================================
    # REPORTS
    # =====================================================

    path(
        'reports/',
        views.financial_report,
        name='financial_report'
    ),
    path(
        "receivables/<int:pk>/",
        views.receivable_detail,
        name="receivable_detail",
    ),

    path(
        "receivables/<int:pk>/payments/add/",
        views.record_receivable_payment,
        name="record_receivable_payment",
    ),

    # =================================================
    # COUNTERPARTIES
    # =================================================

    path(
        "counterparties/find/",
        views.counterparty_phone_lookup,
        name="counterparty_phone_lookup",
    ),
    path(
        "counterparties/new/",
        views.counterparty_create,
        name="counterparty_create",
    ),
    path(
        "counterparties/<int:pk>/",
        views.counterparty_detail,
        name="counterparty_detail",
    ),
    path(
        "counterparties/<int:counterparty_pk>/debts/new/",
        views.counterparty_debt_create,
        name="counterparty_debt_create",
    ),
    path(
        "debts/", views.debt_list, name="debt_list",
    ),
    path("debts/export.csv", views.debt_report_csv, name="debt_report_csv"),
    path("debts/export.pdf", views.debt_report_pdf, name="debt_report_pdf"),
    path(
        'receivables/create/',
        views.receivable_create,
        name='receivable_create'
    ),

]
