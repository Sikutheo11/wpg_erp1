from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
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

    def _grant(self, codename):
        group, _ = Group.objects.get_or_create(name="Inventory Test Group")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="inventory",
                codename=codename,
            )
        )
        self.user.groups.add(group)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("inventory:product_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_authenticated_user_without_permission_is_forbidden(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("inventory:product_list"))

        self.assertEqual(response.status_code, 403)

    def test_product_list_renders_for_group_member(self):
        self._grant("view_product")
        self.client.force_login(self.user)

        response = self.client.get(reverse("inventory:product_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Products")
        self.assertNotContains(response, "Add Product")

    def test_add_permission_shows_product_create_action(self):
        self._grant("view_product")
        self._grant("add_product")
        self.client.force_login(self.user)

        response = self.client.get(reverse("inventory:product_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("inventory:product_create"),
        )
