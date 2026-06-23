from django.contrib import admin
from .models import OnlineProduct


@admin.register(OnlineProduct)
class OnlineProductAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'is_published',
        'is_featured',
        'views'
    )

    list_filter = (
        'is_published',
        'is_featured'
    )

    search_fields = (
        'product__name',
        'product__code'
    )

    readonly_fields = (
        'views',
        'created_at',
    )