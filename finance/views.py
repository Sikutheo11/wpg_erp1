from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from django.utils import timezone

from .models import Income, Expense, Receivable, Payable, Payment
from sales.models import Sale


@login_required
def finance_dashboard(request):

    # ================= INCOME =================
    total_income = Income.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    sales_income = Income.objects.filter(
        income_type='sales'
    ).aggregate(total=Sum('amount'))['total'] or 0

    service_income = Income.objects.filter(
        income_type='service'
    ).aggregate(total=Sum('amount'))['total'] or 0


    # ================= EXPENSE =================
    total_expenses = Expense.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    salary_expense = Expense.objects.filter(
        expense_type='salary'
    ).aggregate(total=Sum('amount'))['total'] or 0

    raw_material_expense = Expense.objects.filter(
        expense_type='raw_material'
    ).aggregate(total=Sum('amount'))['total'] or 0


    # ================= PROFIT =================
    net_profit = total_income - total_expenses


    # ================= RECEIVABLES =================
    receivables_balance = Receivable.objects.filter(
        status__in=['unpaid', 'partial', 'overdue']
    ).aggregate(
        total=Sum(F('total_amount') - F('amount_paid'))
    )['total'] or 0

    total_receivables = Receivable.objects.count()
    unpaid_receivables = Receivable.objects.filter(status='unpaid').count()


    # ================= PAYABLES =================
    payables_balance = Payable.objects.filter(
        status__in=['unpaid', 'partial', 'overdue']
    ).aggregate(
        total=Sum(F('total_amount') - F('amount_paid'))
    )['total'] or 0

    total_payables = Payable.objects.count()
    unpaid_payables = Payable.objects.filter(status='unpaid').count()


    # ================= PAYMENTS =================
    total_payments = Payment.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0


    # ================= CASH FLOW =================
    cash_in = total_income + total_payments
    cash_out = total_expenses


    # ================= CONTEXT =================
    context = {
        # Income
        "total_income": total_income,
        "sales_income": sales_income,
        "service_income": service_income,

        # Expense
        "total_expenses": total_expenses,
        "salary_expense": salary_expense,
        "raw_material_expense": raw_material_expense,

        # Profit
        "net_profit": net_profit,

        # Receivables
        "receivables_balance": receivables_balance,
        "total_receivables": total_receivables,
        "unpaid_receivables": unpaid_receivables,

        # Payables
        "payables_balance": payables_balance,
        "total_payables": total_payables,
        "unpaid_payables": unpaid_payables,

        # Payments
        "total_payments": total_payments,

        # Cash flow
        "cash_in": cash_in,
        "cash_out": cash_out,
    }

    return render(request, "finance/finance_dashboard.html", context)