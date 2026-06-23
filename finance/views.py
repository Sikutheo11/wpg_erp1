from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone

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



# =====================================================
# FINANCE DASHBOARD
# =====================================================

@login_required
def finance_dashboard(request):

    accounts = Account.objects.all()


    total_cash = accounts.aggregate(
        total=Sum('balance')
    )['total'] or 0



    total_income = Income.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0



    total_expense = Expense.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0



    receivable = Receivable.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0



    payable = Payable.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0



    profit = (
        total_income
        -
        total_expense
    )



    recent_transactions = Transaction.objects.all().order_by(
        '-created_at'
    )[:10]

    cash_balance = Account.objects.aggregate(
        total=Sum('balance')
    )['total'] or 0



    context={

        "accounts":accounts,

        "cash_balance":total_cash,

        "income":total_income,

        "expense":total_expense,

        "receivable":receivable,

        "payable":payable,

        "profit":profit,

        "transactions":recent_transactions,
        "cash_balance": cash_balance,

    }



    return render(
        request,
        "finance/dashboard.html",
        context
    )






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