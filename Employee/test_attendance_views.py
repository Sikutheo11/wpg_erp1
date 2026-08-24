from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from Employee.models import Attendance, Department, Employee


class AttendanceViewScopeTests(TestCase):
    password = "Strong-Test-Password-2026"

    def user(self, username, group):
        user = get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            first_name=username.title(),
            last_name="Tester",
            password=self.password,
        )
        user.groups.add(Group.objects.get_or_create(name=group)[0])
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="Employee", codename="view_attendance"
            ),
            Permission.objects.get(
                content_type__app_label="Employee", codename="add_attendance"
            ),
        )
        return user

    def setUp(self):
        self.manager = self.user("attendance-manager", "Manager")
        self.worker = self.user("attendance-worker", "Worker")
        self.other_worker = self.user("attendance-other", "Worker")
        self.hr = self.user("attendance-hr", "HR Manager")
        self.furniture = Department.objects.create(
            name="furniture", business_unit="FURNITURE", manager=self.manager
        )
        self.construction = Department.objects.create(
            name="construction", business_unit="CONSTRUCTION"
        )
        self.worker_employee = Employee.objects.create(
            user=self.worker,
            department=self.furniture,
            national_id="ATT-001",
            emergency_contact="0788000001",
        )
        self.other_employee = Employee.objects.create(
            user=self.other_worker,
            department=self.construction,
            national_id="ATT-002",
            emergency_contact="0788000002",
        )
        Attendance.objects.create(
            employee=self.worker_employee, date=date(2026, 8, 24), status="present"
        )
        Attendance.objects.create(
            employee=self.other_employee, date=date(2026, 8, 24), status="absent"
        )

    def test_worker_only_sees_own_attendance(self):
        self.client.force_login(self.worker)
        response = self.client.get(reverse("employee:attendance_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.worker_employee))
        self.assertNotContains(response, str(self.other_employee))

    def test_department_manager_only_sees_managed_department(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("employee:attendance_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.worker_employee))
        self.assertNotContains(response, str(self.other_employee))

    def test_hr_sees_company_attendance(self):
        self.client.force_login(self.hr)
        response = self.client.get(reverse("employee:attendance_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.worker_employee))
        self.assertContains(response, str(self.other_employee))

    def test_worker_attendance_form_is_locked_to_worker(self):
        self.client.force_login(self.worker)
        response = self.client.get(reverse("employee:attendance_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="employee"')
        self.assertContains(response, "disabled")
        self.assertNotContains(response, str(self.other_employee))
