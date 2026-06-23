from django.contrib import admin

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



# =====================================================
# ACCOUNT ADMIN
# =====================================================

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'account_type',
        'account_number',
        'balance',
        'created_at'
    )

    search_fields = (
        'name',
        'account_number'
    )

    list_filter = (
        'account_type',
    )





# =====================================================
# TRANSACTION ADMIN
# =====================================================

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    list_display = (
        'account',
        'transaction_type',
        'amount',
        'description',
        'date'
    )

    list_filter = (
        'transaction_type',
        'date'
    )

    search_fields = (
        'description',
    )





# =====================================================
# INCOME ADMIN
# =====================================================

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'income_type',
        'amount',
        'account',
        'date'
    )

    list_filter = (
        'income_type',
        'date'
    )

    search_fields = (
        'title',
    )





# =====================================================
# EXPENSE ADMIN
# =====================================================

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'expense_type',
        'amount',
        'account',
        'supplier',
        'date'
    )


    list_filter = (
        'expense_type',
        'date'
    )


    search_fields = (
        'title',
    )





# =====================================================
# RECEIVABLE ADMIN
# =====================================================

@admin.register(Receivable)
class ReceivableAdmin(admin.ModelAdmin):

    list_display = (
        'invoice_number',
        'customer',
        'total_amount',
        'amount_paid',
        'status',
        'due_date'
    )


    list_filter = (
        'status',
        'due_date'
    )


    search_fields = (
        'invoice_number',
        'customer__email'
    )





# =====================================================
# PAYABLE ADMIN
# =====================================================

@admin.register(Payable)
class PayableAdmin(admin.ModelAdmin):

    list_display = (
        'reference',
        'supplier',
        'total_amount',
        'amount_paid',
        'status',
        'due_date'
    )


    list_filter = (
        'status',
        'due_date'
    )


    search_fields = (
        'reference',
        'supplier__name'
    )





# =====================================================
# PAYMENT ADMIN
# =====================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        'amount',
        'method',
        'receivable',
        'payable',
        'date'
    )


    list_filter = (
        'method',
        'date'
    )





# =====================================================
# PAYROLL ADMIN
# =====================================================

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'month',
        'basic_salary',
        'gross_salary',
        'net_salary'
    )


    list_filter = (
        'month',
    )


    search_fields = (
        'employee__user__first_name',
        'employee__user__last_name'
    )