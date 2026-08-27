from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from Employee.models import Employee
from furniture.lifecycle_service import FurnitureProductionLifecycleService
from furniture.models import (
    ProductionJob,
    ProductionOutput,
    QualityInspection,
)
from inventory.models import (
    Product,
    StockMovement,
    Warehouse,
)


class FinishedGoodsReleaseTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="finished-goods-admin@example.com",
            username="finished-goods-admin",
            first_name="Finished",
            last_name="Goods",
            password="Strong-Test-Password-2026!",
        )

        self.employee = Employee.objects.create(
            user=self.user,
            national_id="FINISHED-GOODS-001",
            emergency_contact="0788000020",
        )

        self.product = Product.objects.create(
            name="Quality Approved Desk",
            product_code="QA-DESK-001",
            business_unit="FURNITURE",
            product_type="FINISHED_GOOD",
            standard_cost=Decimal("50000.00"),
            track_inventory=False,
        )

        self.job = ProductionJob.objects.create(
            product=self.product,
            status="QUALITY_CHECK",
            quantity_to_produce=10,
            created_by=self.employee,
        )

        self.output = ProductionOutput.objects.create(
            production_job=self.job,
            product=self.product,
            quantity_produced=10,
            produced_by=self.employee,
        )

        self.finished_warehouse = Warehouse.objects.create(
            name="Furniture Finished Goods",
            warehouse_type="FINISHED_GOODS",
            business_unit="FURNITURE",
            is_active=True,
        )

        self.main_warehouse = Warehouse.objects.create(
            name="Furniture Main Store",
            warehouse_type="MAIN",
            business_unit="FURNITURE",
            is_active=True,
        )

    def make_inspection(
        self,
        *,
        result="PASSED",
        approved=False,
        quantity_passed=10,
        quantity_failed=0,
    ):
        return QualityInspection.objects.create(
            production_job=self.job,
            inspection_type="FINAL",
            result=result,
            inspector=self.employee,
            quantity_inspected=10,
            quantity_passed=quantity_passed,
            quantity_failed=quantity_failed,
            score=100 if result == "PASSED" else 50,
            approved_by=self.employee if approved else None,
            approved_at=timezone.now() if approved else None,
        )

    def test_passed_but_not_approved_cannot_be_ready(self):
        inspection = self.make_inspection(
            result="PASSED",
            approved=False,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Final inspection must be formally approved.",
        ):
            FurnitureProductionLifecycleService.mark_ready_for_finished_goods(
                inspection
            )

        self.job.refresh_from_db()
        self.assertEqual(
            self.job.status,
            "QUALITY_CHECK",
        )

    def test_failed_final_inspection_cannot_be_ready(self):
        inspection = self.make_inspection(
            result="FAILED",
            approved=True,
            quantity_passed=0,
            quantity_failed=10,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "A PASSED final inspection is required.",
        ):
            FurnitureProductionLifecycleService.mark_ready_for_finished_goods(
                inspection
            )

    def test_approved_final_inspection_moves_job_to_ready(self):
        inspection = self.make_inspection(
            result="PASSED",
            approved=True,
        )

        FurnitureProductionLifecycleService.mark_ready_for_finished_goods(
            inspection
        )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "READY_FOR_FINISHED_GOODS",
        )

        self.assertFalse(
            StockMovement.objects.filter(
                reference_type="PRODUCTION_JOB",
                reference_id=str(self.job.pk),
            ).exists()
        )

    def test_wrong_warehouse_cannot_receive_finished_goods(self):
        inspection = self.make_inspection(
            result="PASSED",
            approved=True,
        )

        FurnitureProductionLifecycleService.mark_ready_for_finished_goods(
            inspection
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Select an active Furniture FINISHED_GOODS warehouse.",
        ):
            FurnitureProductionLifecycleService.release_to_finished_goods(
                production_job=self.job,
                warehouse=self.main_warehouse,
                actor=self.user,
            )

    def test_release_creates_single_inventory_receipt(self):
        inspection = self.make_inspection(
            result="PASSED",
            approved=True,
        )

        FurnitureProductionLifecycleService.mark_ready_for_finished_goods(
            inspection
        )

        released = (
            FurnitureProductionLifecycleService.release_to_finished_goods(
                production_job=self.job,
                warehouse=self.finished_warehouse,
                actor=self.user,
            )
        )

        self.assertEqual(
            len(released),
            1,
        )

        self.output.refresh_from_db()
        self.job.refresh_from_db()
        self.product.refresh_from_db()

        self.assertIsNotNone(
            self.output.inventory_movement_id
        )

        self.assertEqual(
            self.job.status,
            "FINISHED_GOODS",
        )

        self.assertTrue(
            self.product.track_inventory
        )

        movement = StockMovement.objects.get(
            reference_type="PRODUCTION_JOB",
            reference_id=str(self.job.pk),
        )

        self.assertEqual(
            movement.product,
            self.product,
        )

        self.assertEqual(
            movement.warehouse,
            self.finished_warehouse,
        )

        self.assertEqual(
            movement.quantity,
            Decimal("10"),
        )

        self.assertEqual(
            movement.movement_type,
            "IN",
        )

        self.assertEqual(
            movement.status,
            "POSTED",
        )

    def test_same_output_cannot_enter_inventory_twice(self):
        inspection = self.make_inspection(
            result="PASSED",
            approved=True,
        )

        FurnitureProductionLifecycleService.mark_ready_for_finished_goods(
            inspection
        )

        FurnitureProductionLifecycleService.release_to_finished_goods(
            production_job=self.job,
            warehouse=self.finished_warehouse,
            actor=self.user,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Job must be READY FOR FINISHED GOODS.",
        ):
            FurnitureProductionLifecycleService.release_to_finished_goods(
                production_job=self.job,
                warehouse=self.finished_warehouse,
                actor=self.user,
            )

        self.assertEqual(
            StockMovement.objects.filter(
                reference_type="PRODUCTION_JOB",
                reference_id=str(self.job.pk),
                movement_type="IN",
                status="POSTED",
            ).count(),
            1,
        )
