# Employee/dashboard.py


from django.db.models import Count, Sum
from django.utils import timezone

from .models import (
    Employee,
    Department,
    Position,
    Attendance,
    Leave,
)



def get_employee_dashboard(user):

    today = timezone.now().date()


    # ===============================
    # EMPLOYEE SUMMARY
    # ===============================

    total_employees = Employee.objects.count()


    active_employees = Employee.objects.filter(
        is_active=True
    ).count()


    inactive_employees = Employee.objects.filter(
        is_active=False
    ).count()



    # ===============================
    # DEPARTMENT / POSITION
    # ===============================

    total_departments = Department.objects.count()


    total_positions = Position.objects.count()



    # ===============================
    # ATTENDANCE
    # ===============================

    present_today = Attendance.objects.filter(
        date=today,
        status="Present"
    ).count()


    absent_today = Attendance.objects.filter(
        date=today,
        status="Absent"
    ).count()



    # ===============================
    # LEAVE
    # ===============================

    pending_leaves = Leave.objects.filter(
        status="Pending"
    ).count()



    # ===============================
    # ANALYTICS
    # ===============================

    employees_by_department = (
        Employee.objects
        .values(
            "department__name"
        )
        .annotate(
            total=Count("id")
        )
    )


    employees_by_position = (
        Employee.objects
        .values(
            "position__title"
        )
        .annotate(
            total=Count("id")
        )
    )



    # ===============================
    # ALERTS
    # ===============================

    alerts = []


    if inactive_employees:

        alerts.append(
            "Some employees are inactive"
        )


    if total_employees == 0:

        alerts.append(
            "No employees registered"
        )


    if pending_leaves:

        alerts.append(
            f"{pending_leaves} leave requests pending"
        )



    # ===============================
    # RECENT EMPLOYEES
    # ===============================

    recent_employees = (
        Employee.objects
        .order_by("-id")[:10]
    )



    return {

        "total_employees":
            total_employees,


        "active_employees":
            active_employees,


        "inactive_employees":
            inactive_employees,


        "total_departments":
            total_departments,


        "total_positions":
            total_positions,


        "present_today":
            present_today,


        "absent_today":
            absent_today,


        "pending_leaves":
            pending_leaves,


        "employees_by_department":
            employees_by_department,


        "employees_by_position":
            employees_by_position,


        "recent_employees":
            recent_employees,


        "alerts":
            alerts,

    }