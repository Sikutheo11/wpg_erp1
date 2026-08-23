from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse


class SalesViewPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="sales-access@example.com",
            username="sales-access",
            first_name="Sales",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("sales:customer_list"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_without_permission_is_denied(self):
        self.client.force_login(self.user)
        for name in (
            "sales:customer_list",
            "sales:quotation_list",
            "sales:sale_list",
            "sales:invoice_list",
            "sales:payment_list",
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_group_permission_grants_customer_list_access(self):
        group = Group.objects.create(name="Customer Viewers")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="sales",
                codename="view_customer",
            )
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

        with patch(
            "sales.views.render",
            return_value=HttpResponse("Customers"),
        ):
            response = self.client.get(reverse("sales:customer_list"))

        self.assertEqual(response.status_code, 200)

    def test_quotation_approval_requires_post(self):
        group = Group.objects.create(name="Quotation Approvers")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="sales",
                codename="approve_salesquotation",
            )
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("sales:quotation_approve", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, 405)
