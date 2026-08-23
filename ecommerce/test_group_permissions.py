from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse

from core.permissions import PermissionService


class EcommerceGroupPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="marketplace-access@example.com",
            username="marketplace-access",
            first_name="Marketplace",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

    def _grant(self, codename):
        group, _ = Group.objects.get_or_create(name="Marketplace Test Group")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="ecommerce",
                codename=codename,
            )
        )
        self.user.groups.add(group)

    def test_public_shop_does_not_require_staff_permission(self):
        with patch(
            "ecommerce.views.render",
            return_value=HttpResponse("Shop"),
        ):
            response = self.client.get(reverse("ecommerce:shop"))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_management_user_is_redirected(self):
        response = self.client.get(reverse("ecommerce:online_product_list"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_without_permission_is_denied(self):
        self.client.force_login(self.user)
        for name in (
            "ecommerce:ecommerce_dashboard",
            "ecommerce:online_product_list",
            "ecommerce:payment_list",
            "ecommerce:marketplace_seller_list",
            "ecommerce:seller_settlement_list",
            "ecommerce:marketplace_report",
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_native_group_permission_grants_product_list_access(self):
        self._grant("view_onlineproduct")
        self.client.force_login(self.user)
        with patch(
            "ecommerce.views.render",
            return_value=HttpResponse("Online products"),
        ):
            response = self.client.get(reverse("ecommerce:online_product_list"))
        self.assertEqual(response.status_code, 200)

    def test_product_view_does_not_grant_change(self):
        self._grant("view_onlineproduct")
        self.assertTrue(
            PermissionService.user_can_access_feature(
                self.user,
                "MARKETPLACE_PRODUCTS",
                "view",
            )
        )
        self.assertFalse(
            PermissionService.user_can_access_feature(
                self.user,
                "MARKETPLACE_PRODUCTS",
                "edit",
            )
        )

    def test_payment_confirmation_does_not_grant_refund(self):
        self._grant("confirm_ecommercepayment")
        self.assertTrue(
            PermissionService.user_can_access_feature(
                self.user,
                "MARKETPLACE_PAYMENT_CONFIRM",
                "approve",
            )
        )
        self.assertFalse(
            PermissionService.user_can_access_feature(
                self.user,
                "MARKETPLACE_PAYMENT_REFUND",
                "approve",
            )
        )

    def test_settlement_approval_requires_permission_and_post(self):
        self._grant("approve_sellersettlement")
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "ecommerce:seller_settlement_approve",
                kwargs={"pk": 999999},
            )
        )
        self.assertEqual(response.status_code, 405)

    def test_non_staff_group_member_can_reach_settlement_payment_form(self):
        self._grant("pay_sellersettlement")
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "ecommerce:seller_settlement_pay",
                kwargs={"pk": 999999},
            )
        )
        self.assertEqual(response.status_code, 404)
