from django.urls import path
from . import views
app_name = "finance"


urlpatterns = [

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



    # =====================================================
    # INCOME
    # =====================================================

    path(
        'income/',
        views.income_list,
        name='income_list'
    ),




    # =====================================================
    # EXPENSE
    # =====================================================

    path(
        'expenses/',
        views.expense_list,
        name='expense_list'
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

]