from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Count
from finance.models import Income, Expense, Receivable, Payable
from inventory.models import RawMaterial, Asset, Product
from furniture.models import Order
from Construction.models import Project
from Employee.models import Employee, Contact, Department, Position
from django.utils import timezone

@login_required
def hr_dashboard(request):

    # ================= EMPLOYEES =================
    total_employees = Employee.objects.count()

    active_employees = Employee.objects.filter(is_active=True).count()
    inactive_employees = Employee.objects.filter(is_active=False).count()

    # ================= DEPARTMENTS =================
    total_departments = Department.objects.count()

    # ================= POSITIONS =================
    total_positions = Position.objects.count()

    # ================= BREAKDOWN =================
    employees_by_department = Employee.objects.values(
        'department__name'
    ).annotate(total=Count('id'))

    employees_by_position = Employee.objects.values(
        'position__title'
    ).annotate(total=Count('id'))

    # ================= ALERTS =================
    alerts = []

    if inactive_employees > 0:
        alerts.append("⚠️ Some employees are inactive")

    if total_employees == 0:
        alerts.append("❌ No employees registered")

    # ================= CONTEXT =================
    context = {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "inactive_employees": inactive_employees,

        "total_departments": total_departments,
        "total_positions": total_positions,

        "employees_by_department": employees_by_department,
        "employees_by_position": employees_by_position,

        "alerts": alerts,
    }

    return render(request, "hr/manager_dashboard.html", context)

