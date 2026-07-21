from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("subtotal",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "order_type",
        "status",
        "total_amount",
        "created_at",
    )

    list_filter = (
        "order_type",
        "status",
        "created_at",
    )

    search_fields = (
        "customer_name",
        "customer_phone",
        "customer_email",
    )

    readonly_fields = ("created_at",)

    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "product",
        "quantity",
        "price",
    )

    search_fields = (
        "order__customer_name",
        "product__name",
    )
