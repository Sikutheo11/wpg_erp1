# Finance/dashboard.py


from django.db.models import Sum

from .models import (
    Account,
    Transaction,
    Income,
    Expense,
    Receivable,
    Payable,
    Payment,
    Payroll,
)



def get_finance_dashboard(user):


    # ==========================
    # ACCOUNTS
    # ==========================

    total_accounts = Account.objects.count()


    total_balance = (
        Account.objects.aggregate(
            total=Sum("balance")
        )["total"] or 0
    )



    # ==========================
    # INCOME
    # ==========================

    total_income = (
        Income.objects.aggregate(
            total=Sum("amount")
        )["total"] or 0
    )



    # ==========================
    # EXPENSE
    # ==========================

    total_expense = (
        Expense.objects.aggregate(
            total=Sum("amount")
        )["total"] or 0
    )



    # ==========================
    # PROFIT
    # ==========================

    profit = total_income - total_expense



    # ==========================
    # RECEIVABLE
    # ==========================

    total_receivable = (
        Receivable.objects.aggregate(
            total=Sum("total_amount")
        )["total"] or 0
    )


    paid_receivable = (
        Receivable.objects.aggregate(
            total=Sum("amount_paid")
        )["total"] or 0
    )


    pending_receivable = (
        total_receivable - paid_receivable
    )



    # ==========================
    # PAYABLE
    # ==========================

    total_payable = (
        Payable.objects.aggregate(
            total=Sum("total_amount")
        )["total"] or 0
    )


    paid_payable = (
        Payable.objects.aggregate(
            total=Sum("amount_paid")
        )["total"] or 0
    )


    pending_payable = (
        total_payable - paid_payable
    )



    # ==========================
    # PAYROLL
    # ==========================

    current_payroll = (
        Payroll.objects.aggregate(
            total=Sum("net_salary")
        )["total"] or 0
    )



    # ==========================
    # TRANSACTIONS
    # ==========================

    recent_transactions = (
        Transaction.objects
        .select_related("account")
        .order_by("-created_at")[:10]
    )



    context = {


        "total_accounts": total_accounts,

        "total_balance": total_balance,


        "total_income": total_income,

        "total_expense": total_expense,

        "profit": profit,


        "total_receivable": total_receivable,

        "pending_receivable": pending_receivable,


        "total_payable": total_payable,

        "pending_payable": pending_payable,


        "current_payroll": current_payroll,


        "recent_transactions": recent_transactions,

    }


    return context