from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from Employee.models import Employee
from inventory.models import Product, RawMaterial

from .forms import ProductionSettingsForm
from .models import BillOfMaterial, ProductionJob, ProductionTask, StockReservation
from .services import FurnitureInventoryService, PlanningService


class FurniturePlanningSettingsUxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="planning-admin@example.com",
            username="planning-admin",
            first_name="Planning",
            last_name="Admin",
            password="Strong-Test-Password-2026!",
        )
        self.employee = Employee.objects.create(
            user=self.user,
            national_id="PLANNING-001",
            emergency_contact="0788000030",
        )
        self.product = Product.objects.create(
            name="Planning Desk",
            product_code="PLANNING-DESK-001",
            business_unit="FURNITURE",
        )
        self.job = ProductionJob.objects.create(
            product=self.product,
            status="ORDER_CONFIRMED",
            quantity_to_produce=2,
            created_by=self.employee,
        )

    def test_settings_form_does_not_expose_singleton_active_flag(self):
        form = ProductionSettingsForm()
        self.assertNotIn("is_active", form.fields)

    def test_currency_is_normalized_and_validated(self):
        data = {
            "overhead_rate": "10",
            "wastage_rate": "5",
            "default_transport_cost": "0",
            "default_other_cost": "0",
            "default_labour_hourly_rate": "2500",
            "default_machine_hourly_cost": "3500",
            "vat_rate": "18",
            "target_profit_margin": "25",
            "currency": "rwf",
        }
        form = ProductionSettingsForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["currency"], "RWF")

        data["currency"] = "12"
        form = ProductionSettingsForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("currency", form.errors)

    def test_schedule_requires_tasks_with_positive_hours(self):
        with self.assertRaisesMessage(ValidationError, "Add at least one"):
            PlanningService.schedule_job(self.job)

        task = ProductionTask.objects.create(
            production_job=self.job,
            name="Cutting",
            sequence=1,
            status="PENDING",
            planned_hours=Decimal("0.00"),
        )
        with self.assertRaisesMessage(ValidationError, "Set planned hours above zero"):
            PlanningService.schedule_job(self.job)

        task.planned_hours = Decimal("2.00")
        task.save(update_fields=["planned_hours"])
        PlanningService.schedule_job(self.job)
        task.refresh_from_db()
        self.assertIsNotNone(task.planned_start)
        self.assertIsNotNone(task.planned_end)

    def test_closed_job_cannot_be_scheduled(self):
        self.job.status = "CANCELLED"
        self.job.save(update_fields=["status"])
        with self.assertRaisesMessage(ValidationError, "cannot be scheduled"):
            PlanningService.schedule_job(self.job)

    @patch.object(FurnitureInventoryService, "check_material_availability")
    def test_reservation_service_uses_model_status_codes(self, availability):
        material = RawMaterial.objects.create(
            name="Planning Timber",
            code="PLANNING-TIMBER-001",
            unit="pcs",
            unit_cost=Decimal("5000.00"),
        )
        availability.return_value = {
            "available": True,
            "items": [
                {
                    "raw_material": material,
                    "quantity_required": Decimal("4.00"),
                }
            ],
            "shortages": [],
        }
        FurnitureInventoryService.reserve_materials(
            production_job=self.job,
            performed_by=self.user,
        )
        reservation = StockReservation.objects.get(production_job=self.job)
        self.assertEqual(reservation.status, "RESERVED")

        FurnitureInventoryService.release_reservations(
            production_job=self.job,
            performed_by=self.user,
        )
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, "RELEASED")
