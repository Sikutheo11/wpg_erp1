from datetime import timedelta
from decimal import Decimal

from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (
    Account,
    Expense,
    ExpenseRequest,
    Income,
    IncomeDeclaration,
    Payable,
    Payment,
    Receivable,
    Transaction,
)


ZERO = Decimal("0.00")

MONEY_FIELD = DecimalField(
    max_digits=18,
    decimal_places=2,
)


def _money_sum(queryset, field_name):
    """
    Return a Decimal sum and never return None.
    """

    return queryset.aggregate(
        total=Coalesce(
            Sum(field_name),
            ZERO,
            output_field=MONEY_FIELD,
        )
    )["total"]


def _account_balance_by_name(name):
    """
    Return the combined balance of accounts matching a standard name.
    """

    return (
        Account.objects
        .filter(name__iexact=name)
        .aggregate(
            total=Coalesce(
                Sum("balance"),
                ZERO,
                output_field=MONEY_FIELD,
            )
        )["total"]
    )


def get_finance_dashboard(user=None):
    """
    Build the Finance dashboard context.

    This dashboard is shared across WPG business units and reports:
    - account balances;
    - current-month income, expenses and net profit;
    - receivables and payables;
    - customer and supplier payments;
    - overdue balances;
    - recent payments and transactions;
    - chart-ready monthly income and expense data.
    """

    today = timezone.localdate()
    month_start = today.replace(day=1)

    year_start = today.replace(
        month=1,
        day=1,
    )

    # =====================================================
    # ACCOUNT BALANCES
    # =====================================================

    accounts = Account.objects.all().order_by(
        "name",
    )

    total_account_balance = _money_sum(
        accounts,
        "balance",
    )

    cash_balance = _account_balance_by_name(
        "Cash"
    )

    bank_balance = _account_balance_by_name(
        "Bank"
    )

    mobile_money_balance = (
        _account_balance_by_name(
            "Mobile Money"
        )
    )

    # =====================================================
    # INCOME AND EXPENSES
    # =====================================================

    month_incomes = Income.objects.filter(
        date__range=[
            month_start,
            today,
        ]
    )

    month_expenses = Expense.objects.filter(
        date__range=[
            month_start,
            today,
        ]
    )

    total_income = _money_sum(
        month_incomes,
        "amount",
    )

    total_expenses = _money_sum(
        month_expenses,
        "amount",
    )

    net_profit = (
        total_income
        - total_expenses
    )

    year_income = _money_sum(
        Income.objects.filter(
            date__range=[
                year_start,
                today,
            ]
        ),
        "amount",
    )

    year_expenses = _money_sum(
        Expense.objects.filter(
            date__range=[
                year_start,
                today,
            ]
        ),
        "amount",
    )

    year_net_profit = (
        year_income
        - year_expenses
    )

    # =====================================================
    # RECEIVABLES
    # =====================================================

    receivables = Receivable.objects.select_related(
        "order",
        "customer",
    )

    receivable_balance_expression = (
        ExpressionWrapper(
            F("total_amount")
            - F("amount_paid"),
            output_field=MONEY_FIELD,
        )
    )

    outstanding_receivables = (
        receivables
        .exclude(status="paid")
        .aggregate(
            total=Coalesce(
                Sum(
                    receivable_balance_expression
                ),
                ZERO,
                output_field=MONEY_FIELD,
            )
        )["total"]
    )

    overdue_receivables = receivables.filter(
        due_date__lt=today,
    ).exclude(
        status="paid",
    )

    overdue_receivable_total = (
        overdue_receivables
        .aggregate(
            total=Coalesce(
                Sum(
                    receivable_balance_expression
                ),
                ZERO,
                output_field=MONEY_FIELD,
            )
        )["total"]
    )

    # =====================================================
    # PAYABLES
    # =====================================================

    payables = Payable.objects.select_related(
        "supplier",
    )

    payable_balance_expression = (
        ExpressionWrapper(
            F("total_amount")
            - F("amount_paid"),
            output_field=MONEY_FIELD,
        )
    )

    outstanding_payables = (
        payables
        .exclude(status="paid")
        .aggregate(
            total=Coalesce(
                Sum(
                    payable_balance_expression
                ),
                ZERO,
                output_field=MONEY_FIELD,
            )
        )["total"]
    )

    overdue_payables = payables.filter(
        due_date__lt=today,
    ).exclude(
        status="paid",
    )

    overdue_payable_total = (
        overdue_payables
        .aggregate(
            total=Coalesce(
                Sum(
                    payable_balance_expression
                ),
                ZERO,
                output_field=MONEY_FIELD,
            )
        )["total"]
    )

    # =====================================================
    # PAYMENTS
    # =====================================================

    payments = Payment.objects.select_related(
        "receivable",
        "receivable__order",
        "payable",
        "payable__supplier",
    )

    month_payments = payments.filter(
        date__range=[
            month_start,
            today,
        ]
    )

    customer_payments = month_payments.filter(
        receivable__isnull=False,
    )

    supplier_payments = month_payments.filter(
        payable__isnull=False,
    )

    customer_payment_total = _money_sum(
        customer_payments,
        "amount",
    )

    supplier_payment_total = _money_sum(
        supplier_payments,
        "amount",
    )

    # =====================================================
    # RECENT ACTIVITY
    # =====================================================

    recent_payments = (
        payments
        .order_by(
            "-date",
            "-pk",
        )[:8]
    )

    recent_transactions = (
        Transaction.objects
        .select_related(
            "account",
        )
        .order_by(
            "-date",
            "-created_at",
        )[:8]
    )

    recent_receivables = (
        receivables
        .order_by(
            "-created_at",
        )[:5]
    )

    recent_payables = (
        payables
        .order_by(
            "-created_at",
        )[:5]
    )

    # =====================================================
    # SIX-MONTH CHART DATA
    # =====================================================

    chart_labels = []
    income_chart_data = []
    expense_chart_data = []

    for offset in range(5, -1, -1):
        target_year = today.year
        target_month = (
            today.month - offset
        )

        while target_month <= 0:
            target_month += 12
            target_year -= 1

        month_date = today.replace(
            year=target_year,
            month=target_month,
            day=1,
        )

        if target_month == 12:
            next_month = month_date.replace(
                year=target_year + 1,
                month=1,
                day=1,
            )
        else:
            next_month = month_date.replace(
                month=target_month + 1,
                day=1,
            )

        month_end = (
            next_month
            - timedelta(days=1)
        )

        chart_labels.append(
            month_date.strftime("%b %Y")
        )

        income_chart_data.append(
            float(
                _money_sum(
                    Income.objects.filter(
                        date__range=[
                            month_date,
                            month_end,
                        ]
                    ),
                    "amount",
                )
            )
        )

        expense_chart_data.append(
            float(
                _money_sum(
                    Expense.objects.filter(
                        date__range=[
                            month_date,
                            month_end,
                        ]
                    ),
                    "amount",
                )
            )
        )

    # =====================================================
    # CONTEXT
    # =====================================================

    unit_labels = dict(ExpenseRequest.BUSINESS_UNITS)
    business_unit_summary = []
    for code, label in unit_labels.items():
        unit_income = _money_sum(Income.objects.filter(business_unit=code, date__range=[year_start, today]), "amount")
        unit_expense = _money_sum(Expense.objects.filter(business_unit=code, date__range=[year_start, today]), "amount")
        business_unit_summary.append({
            "code": code,
            "label": label,
            "income": unit_income,
            "expense": unit_expense,
            "net": unit_income - unit_expense,
            "pending_requests": ExpenseRequest.objects.filter(business_unit=code).exclude(status__in=("DRAFT", "COMPLETED", "REJECTED", "CANCELLED")).count(),
            "pending_income": IncomeDeclaration.objects.filter(business_unit=code, status__in=("SUBMITTED", "UNIT_APPROVED")).count(),
        })

    return {
        "today": today,
        "month_start": month_start,

        "accounts": accounts,
        "total_account_balance": total_account_balance,
        "cash_balance": cash_balance,
        "bank_balance": bank_balance,
        "mobile_money_balance": mobile_money_balance,

        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": net_profit,

        "year_income": year_income,
        "year_expenses": year_expenses,
        "year_net_profit": year_net_profit,

        "pending_expense_request_count": ExpenseRequest.objects.exclude(
            status__in=("DRAFT", "COMPLETED", "REJECTED", "CANCELLED")
        ).count(),
        "pending_expense_request_total": _money_sum(
            ExpenseRequest.objects.exclude(status__in=("DRAFT", "COMPLETED", "REJECTED", "CANCELLED")),
            "amount_requested",
        ),
        "pending_income_declaration_count": IncomeDeclaration.objects.filter(
            status__in=("SUBMITTED", "UNIT_APPROVED")
        ).count(),
        "pending_income_declaration_total": _money_sum(
            IncomeDeclaration.objects.filter(status__in=("SUBMITTED", "UNIT_APPROVED")),
            "amount",
        ),
        "business_unit_summary": business_unit_summary,

        "receivable_count": receivables.count(),
        "outstanding_receivables": outstanding_receivables,
        "overdue_receivable_count": (
            overdue_receivables.count()
        ),
        "overdue_receivable_total": (
            overdue_receivable_total
        ),

        "payable_count": payables.count(),
        "outstanding_payables": outstanding_payables,
        "overdue_payable_count": (
            overdue_payables.count()
        ),
        "overdue_payable_total": (
            overdue_payable_total
        ),

        "customer_payment_count": (
            customer_payments.count()
        ),
        "customer_payment_total": (
            customer_payment_total
        ),
        "supplier_payment_count": (
            supplier_payments.count()
        ),
        "supplier_payment_total": (
            supplier_payment_total
        ),

        "recent_payments": recent_payments,
        "recent_transactions": recent_transactions,
        "recent_receivables": recent_receivables,
        "recent_payables": recent_payables,

        "chart_labels": chart_labels,
        "income_chart_data": income_chart_data,
        "expense_chart_data": expense_chart_data,
    }
