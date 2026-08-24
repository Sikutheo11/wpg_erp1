# Employee/views.py


from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.views.decorators.http import require_POST

from core.permissions import wpg_permission_required

from .models import (
    Employee,
    Department,
    Position,
    Attendance,
    Leave,
    Contact,
)

from .forms import (
    EmployeeForm,
    DepartmentForm,
    PositionForm,
    AttendanceForm,
    LeaveForm,
    ContactForm,
)

from .dashboard import get_employee_dashboard



# ==================================================
# DASHBOARD
# ==================================================

@login_required
@wpg_permission_required(
    "Employee.view_employee",
    feature_code="PEOPLE_DASHBOARD",
)
def employee_dashboard(request):

    context = get_employee_dashboard(
        request.user
    )

    return render(
        request,
        "Employee/dashboard.html",
        context
    )



# ==================================================
# EMPLOYEE MANAGEMENT
# ==================================================

@login_required
@wpg_permission_required(
    "Employee.view_employee",
    feature_code="PEOPLE_EMPLOYEES",
)
def employee_list(request):

    employees = Employee.objects.select_related(
        "user",
        "department",
        "position"
    ).all()

    return render(
        request,
        "Employee/employees/list.html",
        {
            "employees": employees
        }
    )



@login_required
@wpg_permission_required(
    "Employee.view_employee",
    feature_code="PEOPLE_EMPLOYEES",
)
def employee_detail(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )

    return render(
        request,
        "Employee/employees/detail.html",
        {
            "employee": employee
        }
    )



@login_required
@wpg_permission_required(
    "Employee.add_employee",
    feature_code="PEOPLE_EMPLOYEES",
    action="add",
)
def employee_create(request):

    form = EmployeeForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Employee created successfully"
        )

        return redirect(
            "employee:employee_list"
        )


    return render(
        request,
        "Employee/employees/form.html",
        {
            "form": form,
            "title": "Create Employee"
        }
    )



@login_required
@wpg_permission_required(
    "Employee.change_employee",
    feature_code="PEOPLE_EMPLOYEES",
    action="change",
)
def employee_update(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )


    form = EmployeeForm(
        request.POST or None,
        instance=employee
    )


    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Employee updated successfully"
        )

        return redirect(
            "employee:employee_list"
        )


    return render(
        request,
        "Employee/employees/form.html",
        {
            "form": form,
            "title": "Update Employee"
        }
    )



@login_required
@wpg_permission_required(
    "Employee.delete_employee",
    feature_code="PEOPLE_EMPLOYEES",
    action="delete",
)
def employee_delete(request, pk):

    employee = get_object_or_404(
        Employee,
        pk=pk
    )


    if request.method == "POST":

        employee.delete()

        messages.success(
            request,
            "Employee deleted"
        )

        return redirect(
            "employee:employee_list"
        )


    return render(
        request,
        "Employee/employees/delete.html",
        {
            "employee": employee
        }
    )



# ==================================================
# DEPARTMENT MANAGEMENT
# ==================================================

@login_required
@wpg_permission_required(
    "Employee.view_department",
    feature_code="PEOPLE_DEPARTMENTS",
)
def department_list(request):

    departments = Department.objects.all()

    return render(
        request,
        "Employee/departments/list.html",
        {
            "departments": departments
        }
    )



@login_required
@wpg_permission_required(
    "Employee.add_department",
    feature_code="PEOPLE_DEPARTMENTS",
    action="add",
)
def department_create(request):

    form = DepartmentForm(
        request.POST or None
    )


    if form.is_valid():

        form.save()

        return redirect(
            "employee:department_list"
        )


    return render(
        request,
        "Employee/departments/form.html",
        {
            "form":form
        }
    )



@login_required
@wpg_permission_required(
    "Employee.change_department",
    feature_code="PEOPLE_DEPARTMENTS",
    action="change",
)
def department_update(request, pk):

    department = get_object_or_404(
        Department,
        pk=pk
    )


    form = DepartmentForm(
        request.POST or None,
        instance=department
    )


    if form.is_valid():

        form.save()

        return redirect(
            "employee:department_list"
        )


    return render(
        request,
        "Employee/departments/form.html",
        {
            "form":form
        }
    )



@login_required
@wpg_permission_required(
    "Employee.delete_department",
    feature_code="PEOPLE_DEPARTMENTS",
    action="delete",
)
def department_delete(request, pk):

    department = get_object_or_404(
        Department,
        pk=pk
    )


    if request.method=="POST":

        department.delete()

        return redirect(
            "employee:department_list"
        )


    return render(
        request,
        "Employee/departments/delete.html",
        {
            "department":department
        }
    )



# ==================================================
# POSITION MANAGEMENT
# ==================================================

@login_required
@wpg_permission_required(
    "Employee.view_position",
    feature_code="PEOPLE_POSITIONS",
)
def position_list(request):

    positions = Position.objects.all()

    return render(
        request,
        "Employee/positions/list.html",
        {
            "positions":positions
        }
    )



@login_required
@wpg_permission_required(
    "Employee.add_position",
    feature_code="PEOPLE_POSITIONS",
    action="add",
)
def position_create(request):

    form = PositionForm(
        request.POST or None
    )


    if form.is_valid():

        form.save()

        return redirect(
            "employee:position_list"
        )


    return render(
        request,
        "Employee/positions/form.html",
        {
            "form":form
        }
    )



@login_required
@wpg_permission_required(
    "Employee.change_position",
    feature_code="PEOPLE_POSITIONS",
    action="change",
)
def position_update(request, pk):

    position = get_object_or_404(
        Position,
        pk=pk
    )


    form = PositionForm(
        request.POST or None,
        instance=position
    )


    if form.is_valid():

        form.save()

        return redirect(
            "employee:position_list"
        )


    return render(
        request,
        "Employee/positions/form.html",
        {
            "form":form
        }
    )



@login_required
@wpg_permission_required(
    "Employee.delete_position",
    feature_code="PEOPLE_POSITIONS",
    action="delete",
)
def position_delete(request, pk):

    position = get_object_or_404(
        Position,
        pk=pk
    )


    if request.method=="POST":

        position.delete()

        return redirect(
            "employee:position_list"
        )


    return render(
        request,
        "Employee/positions/delete.html",
        {
            "position":position
        }
    )



# ==================================================
# ATTENDANCE MANAGEMENT
# ==================================================

def _attendance_queryset_for(user):
    attendance = Attendance.objects.select_related(
        "employee", "employee__user", "employee__department"
    )
    if user.is_superuser:
        return attendance
    groups = set(user.groups.values_list("name", flat=True))
    if groups.intersection({"HR Manager", "CEO", "Administrator"}):
        return attendance
    managed_department_ids = user.managed_departments.values_list("id", flat=True)
    if managed_department_ids:
        return attendance.filter(employee__department_id__in=managed_department_ids)
    return attendance.filter(employee__user=user)

@login_required
@wpg_permission_required(
    "Employee.view_attendance",
    feature_code="PEOPLE_ATTENDANCE",
)
def attendance_list(request):
    attendance = _attendance_queryset_for(request.user).order_by("-date", "employee__user__first_name")
    status = request.GET.get("status", "").strip()
    date = request.GET.get("date", "").strip()
    if status:
        attendance = attendance.filter(status=status)
    if date:
        attendance = attendance.filter(date=date)


    return render(
        request,
        "Employee/attendance/list.html",
        {
            "attendance": attendance,
            "status_choices": Attendance.STATUS_CHOICES,
            "selected_status": status,
            "selected_date": date,
        }
    )



@login_required
@wpg_permission_required(
    "Employee.add_attendance",
    feature_code="PEOPLE_ATTENDANCE",
    action="add",
)
def attendance_create(request):

    form = AttendanceForm(request.POST or None, user=request.user)


    if form.is_valid():

        form.save()
        messages.success(request, "Attendance recorded successfully.")

        return redirect(
            "employee:attendance_list"
        )


    return render(
        request,
        "Employee/attendance/form.html",
        {
            "form":form
        }
    )



@login_required
@wpg_permission_required(
    "Employee.view_attendance",
    feature_code="PEOPLE_ATTENDANCE",
)
def attendance_report(request):

    report = (
        _attendance_queryset_for(request.user)
        .values(
            "employee__user__first_name",
            "employee__user__last_name",
            "employee__department__business_unit",
        )
        .annotate(
            total=Count("id")
        ).order_by("employee__user__first_name", "employee__user__last_name")
    )


    return render(
        request,
        "Employee/attendance/report.html",
        {
            "report":report
        }
    )



# ==================================================
# LEAVE MANAGEMENT
# ==================================================

@login_required
@wpg_permission_required(
    "Employee.view_leave",
    feature_code="PEOPLE_LEAVE",
)
def leave_list(request):

    leaves = Leave.objects.select_related(
        "employee"
    ).all()


    return render(
        request,
        "Employee/leaves/list.html",
        {
            "leaves":leaves
        }
    )



@login_required
@wpg_permission_required(
    "Employee.add_leave",
    feature_code="PEOPLE_LEAVE",
    action="add",
)
def leave_create(request):

    form = LeaveForm(
        request.POST or None
    )


    if form.is_valid():

        form.save()

        return redirect(
            "employee:leave_list"
        )


    return render(
        request,
        "Employee/leaves/form.html",
        {
            "form":form
        }
    )



@login_required
@wpg_permission_required(
    "Employee.approve_leave",
    feature_code="PEOPLE_LEAVE",
    action="approve",
)
@require_POST
def approve_leave(request, pk):

    leave = get_object_or_404(
        Leave,
        pk=pk
    )

    leave.status = "approved"
    leave.save(update_fields=["status", "updated_at"])


    return redirect(
        "employee:leave_list"
    )



@login_required
@wpg_permission_required(
    "Employee.approve_leave",
    feature_code="PEOPLE_LEAVE",
    action="approve",
)
@require_POST
def reject_leave(request, pk):

    leave = get_object_or_404(
        Leave,
        pk=pk
    )

    leave.status = "rejected"
    leave.save(update_fields=["status", "updated_at"])


    return redirect(
        "employee:leave_list"
    )



# ==================================================
# CONTACT MANAGEMENT
# ==================================================

@login_required
@wpg_permission_required(
    "Employee.view_contact",
    feature_code="PEOPLE_CONTACTS",
)
def contact_list(request):

    contacts = Contact.objects.all()

    return render(
        request,
        "Employee/contacts/list.html",
        {
            "contacts":contacts
        }
    )



@login_required
@wpg_permission_required(
    "Employee.add_contact",
    feature_code="PEOPLE_CONTACTS",
    action="add",
)
def contact_create(request):

    form = ContactForm(
        request.POST or None
    )


    if form.is_valid():   

        form.save()

        return redirect(
            "employee:contact_list"
        )


    return render(
        request,
        "Employee/contacts/form.html",
        {
            "form":form
        }
    )



@login_required
@wpg_permission_required(
    "Employee.change_contact",
    feature_code="PEOPLE_CONTACTS",
    action="change",
)
def contact_update(request, pk):

    contact = get_object_or_404(
        Contact,
        pk=pk
    )


    form = ContactForm(
        request.POST or None,
        instance=contact
    )


    if form.is_valid():

        form.save()

        return redirect(
            "employee:contact_list"
        )


    return render(
        request,
        "Employee/contacts/form.html",
        {
            "form":form
        }
    )



@login_required
@wpg_permission_required(
    "Employee.delete_contact",
    feature_code="PEOPLE_CONTACTS",
    action="delete",
)
def contact_delete(request, pk):

    contact = get_object_or_404(
        Contact,
        pk=pk
    )


    if request.method=="POST":

        contact.delete()

        return redirect(
            "employee:contact_list"
        )


    return render(
        request,
        "Employee/contacts/delete.html",
        {
            "contact":contact
        }
    )



# ==================================================
# REPORTS
# ==================================================

@login_required
@wpg_permission_required(
    "Employee.view_employee",
    feature_code="PEOPLE_REPORTS",
)
def employee_report(request):

    employees = Employee.objects.all()

    return render(
        request,
        "Employee/reports/employees.html",
        {
            "employees":employees
        }
    )



@login_required
@wpg_permission_required(
    "Employee.view_leave",
    feature_code="PEOPLE_REPORTS",
)
def leave_report(request):

    leaves = Leave.objects.all()

    return render(
        request,
        "Employee/reports/leaves.html",
        {
            "leaves":leaves
        }
    )
