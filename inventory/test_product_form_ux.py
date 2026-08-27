from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.forms import ProductForm
from inventory.models import Product


class ProductFormUxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="product-catalogue-admin",
            email="product-catalogue-admin@example.com",
            first_name="Product",
            last_name="Administrator",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)

    @staticmethod
    def product_data(**overrides):
        data = {
            "business_unit": "FURNITURE",
            "product_type": "FINISHED_GOOD",
            "product_code": "BED-UX-001",
            "name": "Approved Bed",
            "unit": "pcs",
            "standard_cost": "100000",
            "selling_price": "150000",
            "reorder_level": "1",
            "reorder_quantity": "2",
            "valuation_method": "STANDARD",
            "track_inventory": "on",
            "is_active": "on",
        }
        data.update(overrides)
        return data

    def test_product_form_exposes_catalogue_and_cost_controls(self):
        form = ProductForm()
        for field_name in (
            "business_unit",
            "product_type",
            "standard_cost",
            "selling_price",
            "is_active",
            "is_published",
            "image",
        ):
            self.assertIn(field_name, form.fields)

    def test_inactive_or_zero_price_product_cannot_be_published(self):
        data = self.product_data(
            selling_price="0",
            is_active="",
            is_published="on",
        )
        form = ProductForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("selling_price", form.errors)
        self.assertIn("is_active", form.errors)

    def test_product_create_and_update_pages_render(self):
        response = self.client.get(reverse("inventory:product_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Product identity")
        product = Product.objects.create(
            business_unit="FURNITURE",
            product_type="FINISHED_GOOD",
            product_code="BED-UX-EDIT",
            name="Bed to Edit",
            standard_cost="90000",
            selling_price="140000",
        )
        response = self.client.get(
            reverse("inventory:product_update", args=[product.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save Changes")

    def test_product_can_be_created_then_published(self):
        response = self.client.post(
            reverse("inventory:product_create"),
            self.product_data(is_published="on"),
        )
        self.assertRedirects(response, reverse("inventory:product_list"))
        product = Product.objects.get(product_code="BED-UX-001")
        self.assertTrue(product.is_active)
        self.assertTrue(product.is_published)

