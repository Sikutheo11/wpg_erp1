from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse


class OrderViewPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="order-access@example.com",
            username="order-access",
            first_name="Order",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("orders:order_list"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_without_permission_is_denied(self):
        self.client.force_login(self.user)
        for name in (
            "orders:order_list",
            "orders:business_unit_select",
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_group_permission_grants_order_list_access(self):
        group = Group.objects.create(name="Order Viewers")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="orders",
                codename="view_order",
            )
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

        with patch(
            "orders.views.render",
            return_value=HttpResponse("Orders"),
        ):
            response = self.client.get(reverse("orders:order_list"))

        self.assertEqual(response.status_code, 200)

    def test_order_confirmation_requires_post(self):
        group = Group.objects.create(name="Order Approvers")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="orders",
                codename="approve_order",
            )
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("orders:confirm_order", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, 405)
