from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.forms import StockMovementForm
from inventory.models import Product, StockMovement, Warehouse


class StockMovementUxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="stock-movement-admin",
            email="stock-movement-admin@example.com",
            first_name="Stock",
            last_name="Administrator",
            password="Strong-Test-Password-2026!",
        )
        self.product = Product.objects.create(
            business_unit="FURNITURE",
            product_type="FINISHED_GOOD",
            product_code="STOCK-UX-001",
            name="Stock UX Bed",
            unit="pcs",
            standard_cost="100000",
            selling_price="150000",
        )
        self.warehouse = Warehouse.objects.create(
            name="Stock UX Warehouse",
            warehouse_type="FINISHED_GOODS",
            business_unit="FURNITURE",
        )
        self.client.force_login(self.user)

    def movement_data(self, **overrides):
        data = {
            "product": self.product.pk,
            "warehouse": self.warehouse.pk,
            "movement_type": "IN",
            "quantity": "3",
            "unit_cost": "",
            "reference_type": "PURCHASE",
            "reference_no": "PO-UX-001",
            "notes": "Initial test receipt",
        }
        data.update(overrides)
        return data

    def test_form_uses_product_and_warehouse_not_legacy_material(self):
        form = StockMovementForm()
        self.assertIn("product", form.fields)
        self.assertIn("warehouse", form.fields)
        self.assertNotIn("raw_material", form.fields)
        values = {value for value, label in form.fields["movement_type"].choices}
        self.assertNotIn("TRANSFER_IN", values)
        self.assertNotIn("TRANSFER_OUT", values)

    def test_adjustment_requires_explanation(self):
        form = StockMovementForm(data=self.movement_data(
            movement_type="ADJUSTMENT_IN",
            notes="",
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("notes", form.errors)

    def test_receipt_posts_through_stock_service(self):
        response = self.client.post(
            reverse("inventory:stock_create"),
            self.movement_data(),
        )
        self.assertRedirects(response, reverse("inventory:movement_list"))
        movement = StockMovement.objects.get(reference_no="PO-UX-001")
        self.assertEqual(movement.status, "POSTED")
        self.assertEqual(movement.created_by, self.user)
        self.assertEqual(movement.warehouse, self.warehouse)
        self.assertEqual(movement.unit_cost, Decimal("100000.00"))

    def test_issue_cannot_exceed_available_stock(self):
        response = self.client.post(
            reverse("inventory:stock_create"),
            self.movement_data(
                movement_type="OUT",
                quantity="2",
                reference_type="OTHER",
                reference_no="ISSUE-UX-001",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Insufficient available stock")
        self.assertFalse(
            StockMovement.objects.filter(reference_no="ISSUE-UX-001").exists()
        )
