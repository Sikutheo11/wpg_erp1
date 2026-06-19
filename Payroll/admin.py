from django.contrib import admin
from .models import Payroll


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