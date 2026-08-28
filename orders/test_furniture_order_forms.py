from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .forms import OrderForm, OrderItemForm
from .models import Order


class FurnitureOrderItemFormTests(TestCase):
    def test_production_order_headers_exclude_commercial_pricing(self):
        custom_form = OrderForm(
            order_type="CUSTOM_FURNITURE",
            business_unit="FURNITURE",
        )
        for field_name in (
            "discount",
            "tax",
            "province",
            "district",
            "sector",
            "cell",
            "village",
        ):
            self.assertNotIn(field_name, custom_form.fields)

        for order_type in ("RESTOCK", "NEW_PRODUCT"):
            with self.subTest(order_type=order_type):
                form = OrderForm(
                    order_type=order_type,
                    business_unit="FURNITURE",
                )
                self.assertNotIn("discount", form.fields)
                self.assertNotIn("tax", form.fields)

        for order_type in ("CUSTOM_ORDER", "PROJECT", "MAINTENANCE"):
            with self.subTest(order_type=order_type):
                header = OrderForm(order_type=order_type)
                item = OrderItemForm(order_type=order_type)
                self.assertNotIn("discount", header.fields)
                self.assertNotIn("tax", header.fields)
                self.assertNotIn("price", item.fields)

    def test_ecommerce_only_uses_catalogue_product_fields(self):
        form = OrderItemForm(order_type="ECOMMERCE", business_unit="FURNITURE")
        self.assertEqual(set(form.fields), {"product", "quantity", "specifications"})

    def test_custom_furniture_uses_attachments_without_duplicate_spec_fields(self):
        form = OrderItemForm(order_type="CUSTOM_FURNITURE", business_unit="FURNITURE")
        for field_name in ("reference_image", "design_attachment"):
            self.assertIn(field_name, form.fields)
        for field_name in (
            "length_cm", "width_cm", "height_cm", "material_preference",
            "colour", "finish", "customer_budget",
        ):
            self.assertNotIn(field_name, form.fields)
        self.assertNotIn("price", form.fields)

    def test_restock_uses_product_quantity_and_optional_photo(self):
        form = OrderItemForm(order_type="RESTOCK", business_unit="FURNITURE")
        self.assertEqual(
            set(form.fields),
            {"product", "quantity", "specifications", "reference_image"},
        )

    def test_new_product_requires_design_attachment(self):
        form = OrderItemForm(order_type="NEW_PRODUCT", business_unit="FURNITURE")
        self.assertTrue(form.fields["design_attachment"].required)
        for field_name in (
            "length_cm", "width_cm", "height_cm", "material_preference",
            "colour", "finish", "customer_budget",
        ):
            self.assertNotIn(field_name, form.fields)
        self.assertNotIn("price", form.fields)

    def test_pos_uses_catalogue_product_selection(self):
        form = OrderItemForm(order_type="POS", business_unit="FURNITURE")
        self.assertEqual(set(form.fields), {"product", "quantity", "specifications"})

    def test_duplicate_spec_fields_are_hidden_on_initial_order_page(self):
        request = RequestFactory().get(
            "/orders/create/form/?business_unit=FURNITURE&type=CUSTOM_FURNITURE"
        )
        request.user = AnonymousUser()
        SessionMiddleware(lambda current_request: None).process_request(request)
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
        for field_name in ("reference_image", "design_attachment"):
            self.assertIn(f'name="{field_name}"', html)
        for field_name in (
            "length_cm", "width_cm", "height_cm", "material_preference",
            "colour", "finish", "customer_budget",
        ):
            self.assertNotIn(f'name="{field_name}"', html)
        self.assertNotIn('name="price"', html)


class FurnitureOrderQuotationRoutingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="furniture-order-routing@example.com",
            username="furniture-order-routing",
            first_name="Furniture",
            last_name="Manager",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)

    def test_custom_order_creation_routes_directly_to_quotation_engine(self):
        response = self.client.post(
            reverse("orders:order_create"),
            {
                "business_unit": "FURNITURE",
                "order_type": "CUSTOM_FURNITURE",
                "customer_name": "Custom Bed Customer",
                "customer_phone": "0788000000",
                "customer_email": "customer@example.com",
                "delivery_address": "Rubengera, Karongi",
                "expected_delivery_date": "2026-09-30",
                "notes": "Customer needs a durable double bed.",
                "product_name": "Custom Double Bed",
                "quantity": 2,
                "specifications": "Muvula timber, 160 x 200 cm, natural finish.",
                "length_cm": "200",
                "width_cm": "160",
                "height_cm": "95",
                "material_preference": "Muvula",
                "colour": "Natural wood",
                "finish": "Matte",
                "customer_budget": "450000",
            },
        )

        order = Order.objects.get(customer_name="Custom Bed Customer")
        self.assertIsNotNone(order.customer_quotation_id)
        self.assertEqual(order.status, "QUOTED")
        self.assertRedirects(
            response,
            reverse("sales:quotation_detail", args=[order.customer_quotation_id]),
            fetch_redirect_response=False,
        )
