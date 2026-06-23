from django.contrib import admin

from .models import (
    Customer,
    SalesQuotation,
    SalesQuotationItem,
    Sale,
    SaleItem,
    Invoice,
    CustomerPayment,
)


# ==========================================
# INLINE ITEMS
# ==========================================

class SalesQuotationItemInline(admin.TabularInline):
    model = SalesQuotationItem
    extra = 1
    fields = (
        'product',
        'quantity',
        'unit_price',
        'subtotal_display',
    )
    readonly_fields = (
        'subtotal_display',
    )


    def subtotal_display(self, obj):
        if obj.pk:
            return obj.subtotal
        return 0

    subtotal_display.short_description = "Subtotal"



class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    fields = (
        'product',
        'quantity',
        'unit_price',
        'subtotal_display',
    )

    readonly_fields = (
        'subtotal_display',
    )


    def subtotal_display(self, obj):
        if obj.pk:
            return obj.subtotal
        return 0

    subtotal_display.short_description = "Subtotal"



class CustomerPaymentInline(admin.TabularInline):
    model = CustomerPayment
    extra = 1



# ==========================================
# CUSTOMER ADMIN
# ==========================================

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'company_name',
        'phone',
        'user',
        'created_at',
    )

    search_fields = (
        'company_name',
        'phone',
        'user__username',
    )

    list_filter = (
        'created_at',
    )



# ==========================================
# QUOTATION ADMIN
# ==========================================

@admin.register(SalesQuotation)
class SalesQuotationAdmin(admin.ModelAdmin):

    list_display = (
        'quotation_no',
        'customer',
        'quotation_date',
        'total_amount',
        'status',
    )


    list_filter = (
        'status',
        'quotation_date',
    )


    search_fields = (
        'quotation_no',
        'customer__company_name',
    )


    inlines = [
        SalesQuotationItemInline,
    ]



# ==========================================
# SALE ADMIN
# ==========================================

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):

    list_display = (
        'sale_no',
        'customer',
        'sale_date',
        'total_amount',
        'status',
    )


    list_filter = (
        'status',
        'sale_date',
    )


    search_fields = (
        'sale_no',
        'customer__company_name',
    )


    inlines = [
        SaleItemInline,
    ]



# ==========================================
# INVOICE ADMIN
# ==========================================

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):

    list_display = (
        'invoice_no',
        'sale',
        'total_amount',
        'amount_paid',
        'balance_display',
        'status',
    )


    list_filter = (
        'status',
    )


    search_fields = (
        'invoice_no',
        'sale__sale_no',
    )


    inlines = [
        CustomerPaymentInline,
    ]


    def balance_display(self, obj):
        return obj.balance

    balance_display.short_description = "Balance"



# ==========================================
# PAYMENT ADMIN
# ==========================================

@admin.register(CustomerPayment)
class CustomerPaymentAdmin(admin.ModelAdmin):

    list_display = (
        'invoice',
        'amount',
        'payment_method',
        'payment_date',
    )


    list_filter = (
        'payment_method',
        'payment_date',
    )


    search_fields = (
        'invoice__invoice_no',
        'reference',
    )