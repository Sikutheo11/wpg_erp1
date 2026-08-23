from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from .permissions import user_can_access_agriculture_feature


class AgricultureGroupPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="agriculture-access@example.com",
            username="agriculture-access",
            first_name="Agriculture",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

    def _grant(self, codename):
        group, _ = Group.objects.get_or_create(name="Agriculture Test Group")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="agriculture",
                codename=codename,
            )
        )
        self.user.groups.add(group)

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("agriculture:farm_list"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_without_permission_is_denied(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("agriculture:farm_list"))
        self.assertEqual(response.status_code, 403)

    def test_native_group_permission_grants_farm_access(self):
        self._grant("view_poultryfarm")
        self.client.force_login(self.user)

        with patch(
            "agriculture.views.render",
            return_value=HttpResponse("Farms"),
        ):
            response = self.client.get(reverse("agriculture:farm_list"))

        self.assertEqual(response.status_code, 200)

    def test_view_permission_does_not_grant_add(self):
        self._grant("view_poultryfarm")

        self.assertTrue(
            user_can_access_agriculture_feature(
                self.user,
                "AGRICULTURE_FARMS",
                action="view",
            )
        )
        self.assertFalse(
            user_can_access_agriculture_feature(
                self.user,
                "AGRICULTURE_FARMS",
                action="add",
            )
        )

    def test_operation_approval_is_separate_from_change(self):
        self._grant("change_agricultureoperation")
        self.assertFalse(
            user_can_access_agriculture_feature(
                self.user,
                "AGRICULTURE_OPERATION_APPROVE",
                action="approve",
            )
        )

        self._grant("approve_agricultureoperation")
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.assertTrue(
            user_can_access_agriculture_feature(
                self.user,
                "AGRICULTURE_OPERATION_APPROVE",
                action="approve",
            )
        )
