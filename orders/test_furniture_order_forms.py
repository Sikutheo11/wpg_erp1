from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from .forms import OrderForm, OrderItemForm


class FurnitureOrderItemFormTests(TestCase):
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

    def test_custom_fields_are_visible_on_initial_order_page(self):
        request = RequestFactory().get(
            "/orders/create/form/?business_unit=FURNITURE&type=CUSTOM_FURNITURE"
        )
        request.user = AnonymousUser()
        item_form = OrderItemForm(
            order_type="CUSTOM_FURNITURE",
            business_unit="FURNITURE",
        )
        html = render_to_string(
            "orders/order_form.html",
            {
                "form": OrderForm(
                    order_type="CUSTOM_FURNITURE", business_unit="FURNITURE"
                ),
                "item_form": item_form,
                "business_unit": "FURNITURE",
                "business_unit_display": "Furniture & Manufacturing",
                "order_type": "CUSTOM_FURNITURE",
                "order_type_display": "Custom Furniture Order",
            },
            request=request,
        )
        for field_name in (
            "reference_image", "design_attachment", "length_cm", "width_cm",
            "height_cm", "material_preference", "colour", "finish",
            "customer_budget", "price",
        ):
            self.assertIn(f'name="{field_name}"', html)
