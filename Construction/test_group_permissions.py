from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from core.permissions import PermissionService


class ConstructionGroupPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="construction-access@example.com",
            username="construction-access",
            first_name="Construction",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

    def _grant(self, codename):
        group, _ = Group.objects.get_or_create(name="Construction Test Group")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="Construction",
                codename=codename,
            )
        )
        self.user.groups.add(group)

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("Construction:project_list"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_without_permission_is_denied(self):
        self.client.force_login(self.user)
        for name in (
            "Construction:construction_dashboard",
            "Construction:project_list",
            "Construction:project_create",
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_native_group_permission_grants_project_list_access(self):
        self._grant("view_project")
        self.client.force_login(self.user)
        with patch(
            "Construction.views.render",
            return_value=HttpResponse("Projects"),
        ):
            response = self.client.get(reverse("Construction:project_list"))
        self.assertEqual(response.status_code, 200)

    def test_project_view_does_not_grant_project_add(self):
        self._grant("view_project")
        self.assertTrue(
            PermissionService.user_can_access_feature(
                self.user,
                "CONSTRUCTION_PROJECTS",
                "view",
            )
        )
        self.assertFalse(
            PermissionService.user_can_access_feature(
                self.user,
                "CONSTRUCTION_PROJECTS",
                "add",
            )
        )

    def test_project_add_does_not_grant_material_add(self):
        self._grant("add_project")
        self.assertTrue(
            PermissionService.user_can_access_feature(
                self.user,
                "CONSTRUCTION_PROJECTS",
                "add",
            )
        )
        self.assertFalse(
            PermissionService.user_can_access_feature(
                self.user,
                "CONSTRUCTION_MATERIALS",
                "add",
            )
        )
