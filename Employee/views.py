# Employee/views.py


from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count

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

@login_required
def attendance_list(request):

    attendance = Attendance.objects.select_related(
        "employee"
    ).all()


    return render(
        request,
        "Employee/attendance/list.html",
        {
            "attendance":attendance
        }
    )



@login_required
def attendance_create(request):

    form = AttendanceForm(
        request.POST or None
    )


    if form.is_valid():

        form.save()

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
def attendance_report(request):

    report = (
        Attendance.objects
        .values(
            "employee__user__first_name"
        )
        .annotate(
            total=Count("id")
        )
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
def approve_leave(request, pk):

    leave = get_object_or_404(
        Leave,
        pk=pk
    )

    leave.approved = True
    leave.save()


    return redirect(
        "employee:leave_list"
    )



@login_required
def reject_leave(request, pk):

    leave = get_object_or_404(
        Leave,
        pk=pk
    )

    leave.approved = False
    leave.save()


    return redirect(
        "employee:leave_list"
    )



# ==================================================
# CONTACT MANAGEMENT
# ==================================================

@login_required
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
def leave_report(request):

    leaves = Leave.objects.all()

    return render(
        request,
        "Employee/reports/leaves.html",
        {
            "leaves":leaves
        }
    )