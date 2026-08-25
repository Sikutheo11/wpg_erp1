from django.test import SimpleTestCase

from .forms import OrderItemForm


class FurnitureOrderItemFormTests(SimpleTestCase):
    def test_ecommerce_only_uses_catalogue_product_fields(self):
        form = OrderItemForm(order_type="ECOMMERCE", business_unit="FURNITURE")
        self.assertEqual(set(form.fields), {"product", "quantity", "specifications"})

    def test_custom_furniture_collects_design_and_costing_details(self):
        form = OrderItemForm(order_type="CUSTOM_FURNITURE", business_unit="FURNITURE")
        for field_name in (
            "reference_image", "design_attachment", "length_cm", "width_cm",
            "height_cm", "material_preference", "colour", "finish",
            "customer_budget", "price",
        ):
            self.assertIn(field_name, form.fields)

    def test_restock_uses_product_quantity_and_optional_photo(self):
        form = OrderItemForm(order_type="RESTOCK", business_unit="FURNITURE")
        self.assertEqual(
            set(form.fields),
            {"product", "quantity", "specifications", "reference_image"},
        )

    def test_new_product_requires_design_attachment(self):
        form = OrderItemForm(order_type="NEW_PRODUCT", business_unit="FURNITURE")
        self.assertTrue(form.fields["design_attachment"].required)
        self.assertNotIn("price", form.fields)

    def test_pos_uses_catalogue_product_selection(self):
        form = OrderItemForm(order_type="POS", business_unit="FURNITURE")
        self.assertEqual(set(form.fields), {"product", "quantity", "specifications"})
