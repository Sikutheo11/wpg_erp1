from django.contrib import admin
from .models import *
from sales.models import Sale

# =========================
# ACCOUNT
# =========================
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'account_number', 'balance', 'created_at')
    list_filter = ('account_type',)
    search_fields = ('name', 'account_number')
    ordering = ('-created_at',)


# =========================
# INCOME
# =========================
@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('title', 'income_type', 'amount', 'account', 'date', 'created_at')
    list_filter = ('income_type', 'date')
    search_fields = ('title',)
    ordering = ('-date',)


# =========================
# EXPENSE
# =========================
@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'expense_type', 'amount', 'account', 'supplier', 'date', 'created_at')
    list_filter = ('expense_type', 'date')
    search_fields = ('title',)
    ordering = ('-date',)


# =========================
# ACCOUNTS RECEIVABLE
# =========================
@admin.register(Receivable)
class ReceivableAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number',
        'customer',
        'total_amount',
        'amount_paid',
        'balance',
        'status',
        'due_date'
    )
    list_filter = ('status', 'due_date')
    search_fields = ('invoice_number',)


# =========================
# ACCOUNTS PAYABLE
# =========================
@admin.register(Payable)
class PayableAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'supplier',
        'total_amount',
        'amount_paid',
        'balance',
        'status',
        'due_date'
    )
    list_filter = ('status', 'due_date')
    search_fields = ('reference',)


# =========================
# PAYMENT
# =========================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('amount', 'method', 'receivable', 'payable', 'date')
    list_filter = ('method', 'date')
    search_fields = ('notes',)


# =========================
# PAYROLL
# =========================
@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'month',
        'basic_salary',
        'gross_salary',
        'deductions',
        'net_salary',
        'created_at',
    )

    list_filter = (
        'month',
        'employee',
    )

    search_fields = (
        'employee__name',
        'employee__email',
    )

    ordering = ('-month',)

    readonly_fields = (
        'gross_salary',
        'net_salary',
        'created_at',
    )

    fieldsets = (
        ("Employee Info", {
            'fields': ('employee', 'month')
        }),
        ("Salary Details", {
            'fields': ('basic_salary', 'overtime_hours', 'overtime_rate', 'deductions')
        }),
        ("Calculated Fields", {
            'fields': ('gross_salary', 'net_salary')
        }),
    )