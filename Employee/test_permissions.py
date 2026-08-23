from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch


class EmployeeViewPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="people-access@example.com",
            username="people-access",
            first_name="People",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("employee:employee_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_authenticated_user_without_permission_is_denied(self):
        self.client.force_login(self.user)

        for url_name in (
            "employee:employee_list",
            "employee:department_list",
            "employee:position_list",
            "employee:leave_list",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 403)

    def test_group_permission_grants_employee_list_access(self):
        group = Group.objects.create(name="Employee Viewers")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="Employee",
                codename="view_employee",
            )
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

        # This test verifies authorization independently from the Employee UI
        # templates, which are being modernized in a separate phase.
        with patch(
            "Employee.views.render",
            return_value=HttpResponse("Employee list"),
        ):
            response = self.client.get(reverse("employee:employee_list"))

        self.assertEqual(response.status_code, 200)

    def test_leave_approval_requires_post_after_permission_check(self):
        group = Group.objects.create(name="Leave Approvers")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="Employee",
                codename="approve_leave",
            )
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("employee:approve_leave", kwargs={"pk": 999999})
        )

        self.assertEqual(response.status_code, 405)
