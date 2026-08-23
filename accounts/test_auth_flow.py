from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CustomerRegistrationTests(TestCase):
    def test_self_registration_assigns_customer_group_and_logs_user_in(self):
        response = self.client.post(
            reverse("registerUser"),
            {
                "first_name": "New",
                "last_name": "Customer",
                "email": "customer@example.com",
                "username": "new-customer",
                "phone": "0788123456",
                "password": "Strong-Test-Password-2026!",
                "confirm_password": "Strong-Test-Password-2026!",
            },
        )

        user = get_user_model().objects.get(email="customer@example.com")
        self.assertRedirects(
            response,
            reverse("profile"),
            fetch_redirect_response=False,
        )
        self.assertTrue(user.groups.filter(name="Customer").exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_manager_created_user_is_not_automatically_a_customer(self):
        user = get_user_model().objects.create_user(
            email="employee@example.com",
            username="employee",
            first_name="WPG",
            last_name="Employee",
            password="Strong-Test-Password-2026!",
        )

        self.assertFalse(user.groups.filter(name="Customer").exists())

    def test_logout_requires_post(self):
        user = get_user_model().objects.create_user(
            email="logout@example.com",
            username="logout-user",
            first_name="Logout",
            last_name="User",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(user)

        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))

        self.assertRedirects(
            response,
            reverse("login"),
            fetch_redirect_response=False,
        )
        self.assertNotIn("_auth_user_id", self.client.session)
