from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from .models import Notification


class CoreReportPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="report-access@example.com",
            username="report-access",
            first_name="Report",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

    def _grant(self, app_label, codename):
        group, _ = Group.objects.get_or_create(name="Report Test Group")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            )
        )
        self.user.groups.add(group)

    def test_authenticated_user_cannot_open_finance_report_without_permission(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:finance_report"))
        self.assertEqual(response.status_code, 403)

    def test_native_finance_permission_grants_finance_report(self):
        self._grant("finance", "view_transaction")
        self.client.force_login(self.user)
        with patch("core.views.ReportEngine.generate", return_value={}):
            with patch(
                "core.views.render",
                return_value=HttpResponse("Finance report"),
            ):
                response = self.client.get(reverse("core:finance_report"))
        self.assertEqual(response.status_code, 200)

    def test_executive_report_has_separate_permission(self):
        self._grant("finance", "view_transaction")
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:executive_report"))
        self.assertEqual(response.status_code, 403)

    def test_reports_home_only_contains_allowed_reports(self):
        self._grant("inventory", "view_product")
        self.client.force_login(self.user)

        captured = {}

        def fake_render(request, template, context):
            captured["codes"] = [report.code for report in context["reports"]]
            return HttpResponse("Reports")

        with patch("core.views.render", side_effect=fake_render):
            response = self.client.get(reverse("core:reports_home"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("INVENTORY", captured["codes"])
        self.assertNotIn("FINANCE", captured["codes"])
        self.assertNotIn("EXECUTIVE", captured["codes"])


class NotificationMutationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="notification-owner@example.com",
            username="notification-owner",
            first_name="Notification",
            last_name="Owner",
            password="Strong-Test-Password-2026",
        )
        self.notification = Notification.objects.create(
            user=self.user,
            title="Test notification",
            message="Permission regression test",
        )
        self.client.force_login(self.user)

    def test_mark_read_rejects_get(self):
        response = self.client.get(
            reverse(
                "core:notification_mark_read",
                kwargs={"pk": self.notification.pk},
            )
        )
        self.assertEqual(response.status_code, 405)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_mark_read_accepts_post_for_owner(self):
        response = self.client.post(
            reverse(
                "core:notification_mark_read",
                kwargs={"pk": self.notification.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_mark_all_read_rejects_get(self):
        response = self.client.get(reverse("core:notification_mark_all_read"))
        self.assertEqual(response.status_code, 405)
