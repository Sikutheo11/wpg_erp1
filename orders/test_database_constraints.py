from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from orders.models import Order, OrderItem


class OrderDatabaseConstraintTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            business_unit="FURNITURE",
            order_type="CUSTOM_FURNITURE",
            status="DRAFT",
            customer_name="Constraint Customer",
            customer_phone="0788000000",
        )

    def test_item_quantity_must_be_positive_at_database_level(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderItem.objects.create(
                order=self.order,
                product_name="Invalid item",
                quantity=0,
                price=Decimal("1.00"),
            )

    def test_item_price_cannot_be_negative_at_database_level(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrderItem.objects.create(
                order=self.order,
                product_name="Invalid item",
                quantity=1,
                price=Decimal("-1.00"),
            )

    def test_required_order_constraints_are_declared(self):
        expected = {
            "orders_order_subtotal_nonnegative",
            "orders_order_discount_nonnegative",
            "orders_order_tax_nonnegative",
            "orders_order_total_nonnegative",
            "orders_item_quantity_gt_zero",
            "orders_item_price_nonnegative",
            "orders_item_length_positive_or_null",
            "orders_item_width_positive_or_null",
            "orders_item_height_positive_or_null",
            "orders_item_budget_nonnegative_or_null",
        }
        actual = {
            constraint.name
            for model in (Order, OrderItem)
            for constraint in model._meta.constraints
        }
        self.assertTrue(expected.issubset(actual))
