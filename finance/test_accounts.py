from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from finance.models import Account, Expense, Income


class AccountManagementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="account-manager",
            email="account-manager@example.com",
            first_name="Account",
            last_name="Manager",
            password="Strong-Test-Password-2026",
        )
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label="finance", codename__in=("view_account", "add_account", "change_account", "delete_account")))
        self.client.force_login(self.user)

    def test_account_list_renders_when_accounts_exist(self):
        Account.objects.create(name="Cash", account_type="cash", balance=Decimal("100.00"))
        response = self.client.get(reverse("finance:account_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cash")

    def test_account_can_be_created_and_redirects_to_list(self):
        response = self.client.post(reverse("finance:account_create"), {"name":"WPG Bank", "account_type":"bank", "account_number":"BANK-001", "balance":"50000.00"})
        self.assertRedirects(response, reverse("finance:account_list"))
        self.assertTrue(Account.objects.filter(name="WPG Bank").exists())

    def test_duplicate_account_number_is_rejected(self):
        Account.objects.create(name="First", account_type="bank", account_number="BANK-001")
        response = self.client.post(reverse("finance:account_create"), {"name":"Second", "account_type":"bank", "account_number":"bank-001", "balance":"0.00"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertFalse(Account.objects.filter(name="Second").exists())

    def test_account_can_be_updated(self):
        account = Account.objects.create(name="Old", account_type="cash")
        response = self.client.post(reverse("finance:account_update", args=[account.pk]), {"name":"Main Cash", "account_type":"cash", "account_number":"AUTO-CASH", "balance":"10.00"})
        self.assertRedirects(response, reverse("finance:account_list"))
        account.refresh_from_db()
        self.assertEqual(account.name, "Main Cash")
        self.assertEqual(account.balance, Decimal("0.00"))

    def test_account_delete_requires_post(self):
        account = Account.objects.create(name="Temporary", account_type="cash")
        response = self.client.get(reverse("finance:account_delete", args=[account.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Account.objects.filter(pk=account.pk).exists())
        response = self.client.post(reverse("finance:account_delete", args=[account.pk]))
        self.assertRedirects(response, reverse("finance:account_list"))
        self.assertFalse(Account.objects.filter(pk=account.pk).exists())


class FinanceNavigationRegressionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="finance-navigation",
            email="finance-navigation@example.com",
            first_name="Finance",
            last_name="Navigation",
            password="Strong-Test-Password-2026",
        )
        self.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="finance",
                codename__in=(
                    "view_account", "view_income", "add_income",
                    "view_expense", "add_expense", "view_payment",
                ),
            )
        )
        self.account = Account.objects.create(
            name="Cash", account_type="cash", balance=Decimal("100000.00")
        )
        self.client.force_login(self.user)

    def test_finance_register_pages_render(self):
        for url_name in (
            "finance:account_list",
            "finance:income_list",
            "finance:expense_list",
            "finance:payment_list",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_income_can_be_recorded(self):
        response = self.client.post(
            reverse("finance:income_create"),
            {
                "account": self.account.pk,
                "title": "Cash sale",
                "income_type": "sales",
                "amount": "1000.00",
                "date": "2026-08-24",
                "sale": "",
            },
        )
        self.assertRedirects(response, reverse("finance:income_list"))
        self.assertTrue(Income.objects.filter(title="Cash sale").exists())

    def test_expense_can_be_recorded(self):
        response = self.client.post(
            reverse("finance:expense_create"),
            {
                "account": self.account.pk,
                "title": "Transport",
                "expense_type": "transport",
                "amount": "500.00",
                "date": "2026-08-24",
                "supplier": "",
            },
        )
        self.assertRedirects(response, reverse("finance:expense_list"))
        self.assertTrue(Expense.objects.filter(title="Transport").exists())
