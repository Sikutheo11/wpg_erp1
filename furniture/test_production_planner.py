from datetime import date
from decimal import Decimal

from django.test import TestCase

from furniture.models import ProductionSettings
from furniture.planner_models import (
    ProductionPlan,
    ProductionPlanAdditionalCost,
    ProductionPlanLabour,
    ProductionPlanMachine,
)
from furniture.services.estimation_service import ProductionPlanningCostService
from inventory.models import Asset, RawMaterial


class ProductionPlannerCostingTests(TestCase):
    def setUp(self):
        ProductionSettings.objects.create(
            overhead_rate=Decimal("10.00"),
            wastage_rate=Decimal("5.00"),
            target_profit_margin=Decimal("20.00"),
        )

        self.timber = RawMaterial.objects.create(
            name="Timber",
            code="TIM-PLAN-001",
            unit="m3",
            unit_cost=Decimal("1000.00"),
        )

        self.machine = Asset.objects.create(
            asset_type="machine",
            name="Circular Saw",
            purchase_cost=Decimal("500000.00"),
            purchase_date=date(2026, 1, 1),
        )

        self.plan = ProductionPlan.objects.create(
            name="School Desk",
            quantity=Decimal("100.00"),
            default_wastage_rate=Decimal("5.00"),
            overhead_rate=Decimal("10.00"),
            target_profit_margin=Decimal("20.00"),
        )

        self.plan.materials.create(
            raw_material=self.timber,
            quantity_per_unit=Decimal("2.00"),
        )

        ProductionPlanLabour.objects.create(
            plan=self.plan,
            role_name="Carpentry",
            hours_per_unit=Decimal("1.00"),
            hourly_rate=Decimal("500.00"),
        )

        ProductionPlanMachine.objects.create(
            plan=self.plan,
            asset=self.machine,
            hours_per_unit=Decimal("0.50"),
            hourly_cost=Decimal("200.00"),
        )

        ProductionPlanAdditionalCost.objects.create(
            plan=self.plan,
            cost_type="TRANSPORT",
            description="Delivery",
            amount=Decimal("10000.00"),
        )

    def test_planner_calculates_full_estimate(self):
        result = ProductionPlanningCostService.calculate(self.plan)
        self.plan.refresh_from_db()
        material = self.plan.materials.get()

        self.assertEqual(material.estimated_quantity, Decimal("210.0000"))
        self.assertEqual(material.estimated_cost, Decimal("210000.00"))
        self.assertEqual(self.plan.labour_cost, Decimal("50000.00"))
        self.assertEqual(self.plan.machine_cost, Decimal("10000.00"))
        self.assertEqual(self.plan.direct_cost, Decimal("270000.00"))
        self.assertEqual(self.plan.overhead_cost, Decimal("27000.00"))
        self.assertEqual(self.plan.additional_cost, Decimal("10000.00"))
        self.assertEqual(self.plan.estimated_total_cost, Decimal("307000.00"))
        self.assertEqual(self.plan.estimated_cost_per_unit, Decimal("3070.00"))
        self.assertEqual(
            self.plan.recommended_selling_price,
            Decimal("383750.00"),
        )
        self.assertEqual(self.plan.expected_profit, Decimal("76750.00"))
        self.assertEqual(
            result["estimated_total_cost"],
            Decimal("307000.00"),
        )

    def test_inventory_price_snapshot_changes_only_after_recalculation(self):
        ProductionPlanningCostService.calculate(self.plan)

        line = self.plan.materials.get()
        self.assertEqual(line.unit_cost_snapshot, Decimal("1000.00"))

        self.timber.unit_cost = Decimal("1500.00")
        self.timber.save(update_fields=["unit_cost"])

        line.refresh_from_db()
        self.assertEqual(line.unit_cost_snapshot, Decimal("1000.00"))

        ProductionPlanningCostService.calculate(self.plan)
        line.refresh_from_db()
        self.assertEqual(line.unit_cost_snapshot, Decimal("1500.00"))
