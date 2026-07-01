from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from .dashboard import get_finance_dashboard

from .models import (
    Account,
    Transaction,
    Income,
    Expense,
    Receivable,
    Payable,
    Payment,
    Payroll,
    calculate_financial_summary
)


@login_required
def finance_dashboard(request):
    context = get_finance_dashboard(request.user)

    return render(request, "finance/dashboard.html",context)


# =====================================================
# ACCOUNT
# =====================================================

@login_required
def account_list(request):

    accounts = Account.objects.all()


    return render(
        request,
        "finance/accounts/account_list.html",
        {
            "accounts":accounts
        }
    )






# =====================================================
# INCOME
# =====================================================

@login_required
def income_list(request):

    incomes = Income.objects.all().order_by(
        "-date"
    )


    return render(
        request,
        "finance/income/income_list.html",
        {
            "incomes":incomes
        }
    )







# =====================================================
# EXPENSE
# =====================================================

@login_required
def expense_list(request):

    expenses = Expense.objects.all().order_by(
        "-date"
    )


    return render(
        request,
        "finance/expense/expense_list.html",
        {
            "expenses":expenses
        }
    )







# =====================================================
# RECEIVABLE
# =====================================================

@login_required
def receivable_list(request):

    receivables = Receivable.objects.all().order_by(
        "-created_at"
    )


    return render(
        request,
        "finance/receivable/receivable_list.html",
        {
            "receivables":receivables
        }
    )







# =====================================================
# PAYABLE
# =====================================================

@login_required
def payable_list(request):

    payables = Payable.objects.all().order_by(
        "-created_at"
    )


    return render(
        request,
        "finance/payable/payable_list.html",
        {
            "payables":payables
        }
    )







# =====================================================
# PAYMENT
# =====================================================

@login_required
def payment_list(request):

    payments = Payment.objects.all().order_by(
        "-date"
    )


    return render(
        request,
        "finance/payment/payment_list.html",
        {
            "payments":payments
        }
    )







# =====================================================
# PAYROLL
# =====================================================

@login_required
def payroll_list(request):

    payrolls = Payroll.objects.all().order_by(
        "-month"
    )


    return render(
        request,
        "finance/payroll/payroll_list.html",
        {
            "payrolls":payrolls
        }
    )







# =====================================================
# FINANCIAL REPORT
# =====================================================

@login_required
def financial_report(request):


    start_date = request.GET.get(
        "start"
    )


    end_date = request.GET.get(
        "end"
    )



    if not start_date:

        start_date = timezone.now().date().replace(
            day=1
        )



    if not end_date:

        end_date = timezone.now().date()



    summary = calculate_financial_summary(
        start_date,
        end_date
    )



    context={

        "summary":summary,

        "start_date":start_date,

        "end_date":end_date

    }



    return render(
        request,
        "finance/reports/financial_report.html",
        context
    )