from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from furniture.planner_models import ProductionPlan
from furniture.services.commercial_service import CustomFurnitureQuotationService
from orders.models import Order


class CustomFurnitureQuotationIntegrationTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            business_unit="FURNITURE",
            order_type="CUSTOM_FURNITURE",
            status="AWAITING_QUOTATION",
            customer_name="Karongi School",
            customer_phone="0788000000",
            customer_email="school@example.com",
        )
        self.desks = ProductionPlan.objects.create(
            order=self.order,
            name="School Desk",
            quantity=Decimal("2000.00"),
            status="CALCULATED",
            default_wastage_rate=Decimal("5.00"),
            overhead_rate=Decimal("10.00"),
            target_profit_margin=Decimal("20.00"),
            estimated_total_cost=Decimal("60000000.00"),
            estimated_cost_per_unit=Decimal("30000.00"),
            recommended_selling_price=Decimal("75000000.00"),
            expected_profit=Decimal("15000000.00"),
        )
        self.chairs = ProductionPlan.objects.create(
            order=self.order,
            name="Teacher Chair",
            quantity=Decimal("20.00"),
            status="CALCULATED",
            default_wastage_rate=Decimal("5.00"),
            overhead_rate=Decimal("10.00"),
            target_profit_margin=Decimal("20.00"),
            estimated_total_cost=Decimal("400000.00"),
            estimated_cost_per_unit=Decimal("20000.00"),
            recommended_selling_price=Decimal("500000.00"),
            expected_profit=Decimal("100000.00"),
        )

    def test_one_order_can_have_multiple_production_plans(self):
        self.assertEqual(self.order.furniture_production_plans.count(), 2)

    def test_quotation_is_generated_from_all_calculated_plans(self):
        quotation = CustomFurnitureQuotationService.sync_order_quotation(
            self.order,
            valid_until=timezone.localdate() + timedelta(days=30),
            discount=Decimal("500000.00"),
            tax=Decimal("0.00"),
            notes="School furniture contract.",
        )
        self.order.refresh_from_db()
        self.desks.refresh_from_db()

        self.assertEqual(quotation.items.count(), 2)
        self.assertEqual(quotation.subtotal, Decimal("75500000.00"))
        self.assertEqual(quotation.total_amount, Decimal("75000000.00"))
        self.assertEqual(self.order.status, "AWAITING_CUSTOMER_APPROVAL")
        self.assertEqual(self.order.customer_quotation_id, quotation.pk)
        self.assertEqual(self.desks.sales_quotation_item.quantity, Decimal("2000.00"))
        self.assertEqual(self.desks.sales_quotation_item.unit_price, Decimal("37500.00"))

    def test_refresh_updates_existing_quotation_not_duplicate(self):
        first = CustomFurnitureQuotationService.sync_order_quotation(self.order)

        self.desks.recommended_selling_price = Decimal("76000000.00")
        self.desks.save(update_fields=["recommended_selling_price", "updated_at"])

        second = CustomFurnitureQuotationService.sync_order_quotation(self.order)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.items.count(), 2)
        self.assertEqual(second.subtotal, Decimal("76500000.00"))
