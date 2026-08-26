from django.contrib import admin

from .models import (
    Account,
    Transaction,
    Income,
    IncomeDeclaration,
    Expense,
    ExpenseRequest,
    Receivable,
    Payable,
    Payment,
    Payroll,
    Counterparty,
    ObligationLine,
    ObligationItemGroup,
    ObligationItemType,
)


class ObligationItemTypeInline(admin.TabularInline):
    model = ObligationItemType
    extra = 0


@admin.register(ObligationItemGroup)
class ObligationItemGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "business_unit", "order", "is_active")
    list_filter = ("business_unit", "is_active")
    search_fields = ("name",)
    inlines = (ObligationItemTypeInline,)


@admin.register(ObligationItemType)
class ObligationItemTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "item_group", "default_unit", "order", "is_active")
    list_filter = ("item_group__business_unit", "item_group", "is_active")
    search_fields = ("name",)


class ReceivableLineInline(admin.TabularInline):
    model = ObligationLine
    fk_name = "receivable"
    extra = 0
    readonly_fields = ("line_total",)


class PayableLineInline(ReceivableLineInline):
    fk_name = "payable"


@admin.register(Counterparty)
class CounterpartyAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "is_customer", "is_supplier", "is_active")
    search_fields = ("name", "phone", "email", "tax_number")
    list_filter = ("party_type", "is_customer", "is_supplier", "is_active")



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

    def get_readonly_fields(self, request, obj=None):
        return ("balance",) if obj else ()





# =====================================================
# TRANSACTION ADMIN
# =====================================================

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    readonly_fields = (
        "account", "transaction_type", "amount", "description",
        "date", "created_at", "posting_key",
    )

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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False





# =====================================================
# INCOME ADMIN
# =====================================================

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):

    readonly_fields = tuple(
        field.name for field in Income._meta.fields
    )

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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False





# =====================================================
# EXPENSE ADMIN
# =====================================================

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):

    readonly_fields = tuple(
        field.name for field in Expense._meta.fields
    )

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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IncomeDeclaration)
class IncomeDeclarationAdmin(admin.ModelAdmin):
    list_display = ("declaration_number", "business_unit", "recorded_by", "title", "amount", "status")
    list_filter = ("business_unit", "source_type", "receipt_method", "status")
    search_fields = ("declaration_number", "title", "reference", "recorded_by__first_name", "recorded_by__last_name")
    readonly_fields = ("declaration_number", "unit_approved_by", "unit_approved_at", "finance_confirmed_by", "finance_confirmed_at", "posted_income")


@admin.register(ExpenseRequest)
class ExpenseRequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "requested_by", "title", "amount_requested", "status", "needed_by")
    list_filter = ("status", "request_type", "urgency", "business_unit")
    search_fields = ("request_number", "title", "purpose", "requested_by__first_name", "requested_by__last_name")
    readonly_fields = (
        "request_number", "manager_approved_by", "manager_approved_at",
        "accountant_verified_by", "accountant_verified_at",
        "finance_approved_by", "finance_approved_at",
        "director_approved_by", "director_approved_at", "paid_by", "paid_at",
    )





# =====================================================
# RECEIVABLE ADMIN
# =====================================================

@admin.register(Receivable)
class ReceivableAdmin(admin.ModelAdmin):
    inlines = (ReceivableLineInline,)
    readonly_fields = ("total_amount", "amount_paid", "status")

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
    inlines = (PayableLineInline,)
    readonly_fields = ("total_amount", "amount_paid", "status")

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
