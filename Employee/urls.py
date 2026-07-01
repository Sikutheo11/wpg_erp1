# Employee/urls.py


from django.urls import path

from . import views



app_name = "employee"



urlpatterns = [


    # ==========================================
    # DASHBOARD
    # ==========================================

    path(
        "dashboard/",
        views.employee_dashboard,
        name="employee_dashboard"
    ),



    # ==========================================
    # EMPLOYEE MANAGEMENT
    # ==========================================

    path("employees/",
        views.employee_list,
        name="employee_list"
    ),


    path(
        "employees/create/",
        views.employee_create,
        name="employee_create"
    ),


    path(
        "employees/<int:pk>/",
        views.employee_detail,
        name="employee_detail"
    ),


    path(
        "employees/<int:pk>/update/",
        views.employee_update,
        name="employee_update"
    ),


    path(
        "employees/<int:pk>/delete/",
        views.employee_delete,
        name="employee_delete"
    ),



    # ==========================================
    # DEPARTMENT MANAGEMENT
    # ==========================================

    path(
        "departments/",
        views.department_list,
        name="department_list"
    ),


    path(
        "departments/create/",
        views.department_create,
        name="department_create"
    ),


    path(
        "departments/<int:pk>/update/",
        views.department_update,
        name="department_update"
    ),


    path(
        "departments/<int:pk>/delete/",
        views.department_delete,
        name="department_delete"
    ),



    # ==========================================
    # POSITION MANAGEMENT
    # ==========================================

    path(
        "positions/",
        views.position_list,
        name="position_list"
    ),


    path(
        "positions/create/",
        views.position_create,
        name="position_create"
    ),


    path(
        "positions/<int:pk>/update/",
        views.position_update,
        name="position_update"
    ),


    path(
        "positions/<int:pk>/delete/",
        views.position_delete,
        name="position_delete"
    ),



    # ==========================================
    # ATTENDANCE MANAGEMENT
    # ==========================================

    path(
        "attendance/",
        views.attendance_list,
        name="attendance_list"
    ),


    path(
        "attendance/create/",
        views.attendance_create,
        name="attendance_create"
    ),


    path(
        "attendance/report/",
        views.attendance_report,
        name="attendance_report"
    ),



    # ==========================================
    # LEAVE MANAGEMENT
    # ==========================================

    path(
        "leaves/",
        views.leave_list,
        name="leave_list"
    ),


    path(
        "leaves/create/",
        views.leave_create,
        name="leave_create"
    ),


    path(
        "leaves/<int:pk>/approve/",
        views.approve_leave,
        name="approve_leave"
    ),


    path(
        "leaves/<int:pk>/reject/",
        views.reject_leave,
        name="reject_leave"
    ),



    # ==========================================
    # CONTACT MANAGEMENT
    # ==========================================

    path(
        "contacts/",
        views.contact_list,
        name="contact_list"
    ),


    path(
        "contacts/create/",
        views.contact_create,
        name="contact_create"
    ),


    path(
        "contacts/<int:pk>/update/",
        views.contact_update,
        name="contact_update"
    ),


    path(
        "contacts/<int:pk>/delete/",
        views.contact_delete,
        name="contact_delete"
    ),



    # ==========================================
    # REPORTS
    # ==========================================

    path(
        "reports/employees/",
        views.employee_report,
        name="employee_report"
    ),


    path(
        "reports/attendance/",
        views.attendance_report,
        name="attendance_report_page"
    ),


    path(
        "reports/leaves/",
        views.leave_report,
        name="leave_report"
    ),


]