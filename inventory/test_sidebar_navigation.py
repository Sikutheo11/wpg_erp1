from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class InventorySidebarNavigationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="inventory-sidebar@example.com",
            username="inventory-sidebar",
            first_name="Inventory",
            last_name="Administrator",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)

    def test_inventory_master_tables_render(self):
        for url_name in (
            "inventory:category_list",
            "inventory:warehouse_list",
            "inventory:supplier_list",
            "inventory:asset_assignment_list",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
