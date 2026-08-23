from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse


class FinanceViewPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="finance-access@example.com",
            username="finance-access",
            first_name="Finance",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("finance:debt_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_authenticated_user_without_permission_is_denied(self):
        self.client.force_login(self.user)

        for url_name in (
            "finance:account_list",
            "finance:counterparty_phone_lookup",
            "finance:debt_list",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 403)

    def test_group_permission_grants_debt_list_access(self):
        group = Group.objects.create(name="Debt Viewers")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="finance",
                codename="view_debtrecord",
            )
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

        response = self.client.get(reverse("finance:debt_list"))

        self.assertEqual(response.status_code, 200)

