from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class InventoryViewPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="customer-no-inventory@example.com",
            username="customer-no-inventory",
            first_name="Customer",
            last_name="Only",
            password="Strong-Test-Password-2026!",
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("inventory:product_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_authenticated_user_without_permission_is_forbidden(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("inventory:product_list"))

        self.assertEqual(response.status_code, 403)

