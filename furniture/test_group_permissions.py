from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponse
from django.template.loader import get_template
from django.test import TestCase
from django.urls import reverse

from core.permissions import PermissionService


class FurnitureGroupPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="furniture-access@example.com",
            username="furniture-access",
            first_name="Furniture",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

    def _grant(self, codename):
        group, _ = Group.objects.get_or_create(name="Furniture Test Group")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="furniture",
                codename=codename,
            )
        )
        self.user.groups.add(group)

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("furniture:production_job_list"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_without_permission_is_denied(self):
        self.client.force_login(self.user)
        for name in (
            "furniture:production_job_list",
            "furniture:production_task_list",
            "furniture:quality_inspection_list",
            "furniture:production_reports",
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_native_group_permission_grants_job_list_access(self):
        self._grant("view_productionjob")
        self.client.force_login(self.user)
        with patch(
            "furniture.views.render",
            return_value=HttpResponse("Production jobs"),
        ):
            response = self.client.get(reverse("furniture:production_job_list"))
        self.assertEqual(response.status_code, 200)

    def test_job_view_does_not_grant_change(self):
        self._grant("view_productionjob")
        self.assertTrue(
            PermissionService.user_can_access_feature(
                self.user,
                "FURNITURE_PRODUCTION_JOBS",
                "view",
            )
        )
        self.assertFalse(
            PermissionService.user_can_access_feature(
                self.user,
                "FURNITURE_PRODUCTION_JOBS",
                "change",
            )
        )

    def test_quotation_review_requires_custom_permission_and_allows_get(self):
        self._grant("approve_quotation")
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("furniture:approve_quotation", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, 404)

    def test_permission_aware_action_templates_compile(self):
        for template_name in (
            "furniture/quotation_list.html",
            "furniture/production_task_detail.html",
            "furniture/quality/rework_detail.html",
        ):
            with self.subTest(template_name=template_name):
                self.assertIsNotNone(get_template(template_name))
