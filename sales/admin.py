from django.contrib import admin
from .models import Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    readonly_fields = ('total',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('sale_code', 'customer_name', 'sale_date', 'total', 'status')
    list_filter = ('status', 'sale_date')
    search_fields = ('sale_code', 'customer_name')
    readonly_fields = ('total', 'sale_code')

    inlines = [SaleItemInline]


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product_name', 'quantity', 'unit_price', 'total')
    search_fields = ('product_name',)
    readonly_fields = ('total',)
