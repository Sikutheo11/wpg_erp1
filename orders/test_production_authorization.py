from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from furniture.forms import ProductionJobForm
from furniture.models import Quotation
from furniture.services import ProductionService
from orders.models import Order, OrderItem
from orders.services.order_service import OrderService
from sales.services.quotation_service import QuotationService as SalesQuotationService


class FurnitureProductionAuthorizationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="production-workflow@example.com",
            username="production-workflow",
            first_name="Production",
            last_name="Manager",
            password="Strong-Test-Password-2026!",
        )

    def make_order(self, order_type):
        order = Order.objects.create(
            user=self.user,
            business_unit="FURNITURE",
            order_type=order_type,
            status="DRAFT",
            customer_name="Test Customer",
            customer_phone="0788000000",
        )
        OrderItem.objects.create(
            order=order,
            product_name="Furniture item",
            quantity=2,
            price=0,
            specifications="Approved workshop specification",
        )
        return order

    def test_production_job_form_only_asks_for_order_and_planning_details(self):
        self.assertEqual(
            set(ProductionJobForm().fields),
            {"order", "assigned_to", "description", "expected_end_date"},
        )

    def test_furniture_requests_wait_for_quotation_or_costing(self):
        for order_type in ("CUSTOM_FURNITURE", "RESTOCK", "NEW_PRODUCT"):
            order = self.make_order(order_type)
            OrderService.submit(order=order, actor=self.user)
            order.refresh_from_db()
            self.assertEqual(order.status, "AWAITING_QUOTATION")

    def test_unauthorized_order_is_hidden_and_cannot_create_job(self):
        order = self.make_order("CUSTOM_FURNITURE")
        OrderService.submit(order=order, actor=self.user)

        self.assertNotIn(order, ProductionJobForm().fields["order"].queryset)
        with self.assertRaisesMessage(ValidationError, "not ready for production"):
            ProductionService.create_job(
                order=order,
                product=None,
                job_type="CUSTOMER_CUSTOM",
                quantity_to_produce=2,
                created_by=None,
            )

    def test_approved_internal_costing_authorizes_order(self):
        order = self.make_order("RESTOCK")
        OrderService.submit(order=order, actor=self.user)
        costing = Quotation.objects.create(status="APPROVED", selling_price=100000)

        OrderService.authorize_for_production(
            order=order,
            actor=self.user,
            production_costing=costing,
        )
        order.refresh_from_db()

        self.assertEqual(order.status, "READY_FOR_PRODUCTION")
        self.assertEqual(order.production_costing, costing)
        self.assertIsNotNone(order.production_authorized_at)
        self.assertIn(order, ProductionJobForm().fields["order"].queryset)

    def test_new_product_costing_creates_unpublished_catalogue_product_once(self):
        order = self.make_order("NEW_PRODUCT")
        OrderService.submit(order=order, actor=self.user)
        costing = Quotation.objects.create(
            status="APPROVED",
            material_cost=60000,
            labour_cost=30000,
            selling_price=125000,
        )

        OrderService.authorize_for_production(
            order=order,
            actor=self.user,
            production_costing=costing,
        )

        item = order.items.select_related("product").get()
        product = item.product
        self.assertIsNotNone(product)
        self.assertEqual(product.name, item.product_name)
        self.assertEqual(product.standard_cost, 90000)
        self.assertEqual(product.selling_price, 125000)
        self.assertFalse(product.is_active)
        self.assertFalse(product.is_published)

        OrderService.authorize_for_production(
            order=order,
            actor=self.user,
            production_costing=costing,
        )
        self.assertEqual(order.items.get().product_id, product.pk)

    def test_production_job_page_lists_approved_order_engine_order(self):
        order = self.make_order("RESTOCK")
        order.expected_delivery_date = "2026-09-15"
        order.save(update_fields=["expected_delivery_date", "updated_at"])
        OrderService.submit(order=order, actor=self.user)
        costing = Quotation.objects.create(status="APPROVED", selling_price=100000)
        OrderService.authorize_for_production(
            order=order,
            actor=self.user,
            production_costing=costing,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse("furniture:production_job_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)
        self.assertContains(response, "Order Engine Order")
        self.assertContains(response, "ready for production")

    def test_customer_acceptance_authorizes_custom_order(self):
        order = self.make_order("CUSTOM_FURNITURE")
        OrderService.submit(order=order, actor=self.user)
        quotation = SalesQuotationService.create_from_order(
            order=order,
            actor=self.user,
        )
        item = quotation.items.get()
        item.unit_price = 50000
        item.save(update_fields=["unit_price"])
        SalesQuotationService.submit(quotation=quotation, actor=self.user)

        self.client.force_login(self.user)
        response = self.client.post(
            reverse("sales:customer_quotation_accept", args=[quotation.pk])
        )

        self.assertRedirects(
            response,
            reverse("sales:customer_quotation_detail", args=[quotation.pk]),
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, "READY_FOR_PRODUCTION")
