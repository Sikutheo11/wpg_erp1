from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Order


class OrderTypeCatalogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="order-catalog-manager",
            email="order-catalog-manager@example.com",
            first_name="Order",
            last_name="Manager",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)

    def test_new_order_starts_with_staff_business_units(self):
        response = self.client.get(reverse("orders:business_unit_select"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Furniture &amp; Manufacturing")
        self.assertContains(response, "Construction")
        self.assertContains(response, "Agriculture / Poultry")
        unit_codes = {
            unit["code"]
            for unit in response.context["business_units"]
        }
        self.assertEqual(
            unit_codes,
            {"FURNITURE", "CONSTRUCTION", "AGRICULTURE"},
        )
        self.assertNotIn("MARKETPLACE", unit_codes)

    def test_staff_order_type_select_excludes_ecommerce(self):
        response = self.client.get(
            reverse("orders:order_type_select"),
            {"business_unit": "FURNITURE"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Ecommerce Order")
        self.assertContains(response, "Custom Furniture Order")
        self.assertContains(response, "Restock Existing Product")

    def test_all_orders_starts_with_all_business_units(self):
        response = self.client.get(
            reverse("orders:all_order_business_units")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Furniture &amp; Manufacturing")
        self.assertContains(response, "Marketplace")
        self.assertContains(
            response,
            reverse("orders:all_orders") + "?business_unit=MARKETPLACE",
        )

    def test_staff_cannot_open_ecommerce_create_form(self):
        response = self.client.get(
            reverse("orders:order_create"),
            {"business_unit": "FURNITURE", "type": "ECOMMERCE"},
        )
        self.assertRedirects(response, reverse("orders:business_unit_select"))

    def test_catalog_links_each_type_to_its_filtered_list(self):
        response = self.client.get(reverse("orders:order_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Ecommerce Order")
        self.assertContains(
            response,
            reverse(
                "orders:order_type_orders",
                args=["FURNITURE", "CUSTOM_FURNITURE"],
            ),
        )

    def test_type_list_only_contains_selected_type(self):
        custom = Order.objects.create(
            user=self.user,
            business_unit="FURNITURE",
            order_type="CUSTOM_FURNITURE",
            customer_name="Custom Customer",
            customer_phone="0788000001",
        )
        Order.objects.create(
            user=self.user,
            business_unit="FURNITURE",
            order_type="RESTOCK",
            customer_name="Internal Restock",
            customer_phone="0788000002",
        )
        response = self.client.get(
            reverse(
                "orders:order_type_orders",
                args=["FURNITURE", "CUSTOM_FURNITURE"],
            )
        )
        self.assertContains(response, custom.order_number)
        self.assertNotContains(response, "Internal Restock")
