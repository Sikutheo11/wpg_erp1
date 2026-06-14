from django.contrib import admin
from .models import *


# =========================
# INLINE: Attendance inside Employee
# =========================
class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    readonly_fields = ('hours_worked',)
    can_delete = True


# =========================
# INLINE: Leave inside Employee
# =========================
class LeaveInline(admin.TabularInline):
    model = Leave
    extra = 0
    can_delete = True

# =========================
# DEPARTMENT ADMIN
# =========================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'manager', 'created_at')
    search_fields = ('code', 'name')
    list_filter = ('name',)
    ordering = ('name',)


# =========================
# POSITION ADMIN
# =========================
@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title',)
    search_fields = ('title',)
    list_filter = ('title',)


# =========================
# EMPLOYEE ADMIN
# =========================
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):

    list_display = (
        'employee_code',
        'user',
        'department',
        'position',
        'salary',
        'hourly_rate',
        'is_active',
        'created_at'
    )

    search_fields = (
        'employee_code',
        'user__first_name',
        'user__last_name',
        'national_id'
    )

    list_filter = (
        'department',
        'position',
        'is_active'
    )

    inlines = [
        AttendanceInline,
        LeaveInline,
    ]


# =========================
# ATTENDANCE ADMIN
# =========================
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'date',
        'status',
        'check_in',
        'check_out',
        'hours_worked'
    )

    list_filter = (
        'status',
        'date',
        'employee'
    )

    search_fields = (
        'employee__user__first_name',
        'employee__user__last_name'
    )


# =========================
# LEAVE ADMIN
# =========================
@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'leave_type',
        'start_date',
        'end_date',
        'approved'
    )

    list_filter = (
        'leave_type',
        'approved'
    )

    search_fields = (
        'employee__user__first_name',
        'employee__user__last_name'
    )



