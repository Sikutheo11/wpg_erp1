from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from Employee.models import Employee
from inventory.models import Product

from .forms import ProductionDefectForm, QualityInspectionForm, QualityInspectionResultForm
from .models import ProductionDefect, ProductionJob, QualityInspection, ReworkOrder
from .services import QualityService


class FurnitureQualityReworkUxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="quality-admin@example.com",
            username="quality-admin",
            first_name="Quality",
            last_name="Admin",
            password="Strong-Test-Password-2026!",
        )
        self.employee = Employee.objects.create(
            user=self.user,
            national_id="QUALITY-001",
            emergency_contact="0788000020",
        )
        self.client.force_login(self.user)
        self.product = Product.objects.create(
            name="Quality Desk",
            product_code="QUALITY-DESK-001",
            business_unit="FURNITURE",
        )
        self.job = ProductionJob.objects.create(
            product=self.product,
            status="QUALITY_CHECK",
            quantity_to_produce=10,
            created_by=self.employee,
        )
        self.inspection = QualityInspection.objects.create(
            production_job=self.job,
            inspection_type="FINAL",
            inspector=self.employee,
            result="PENDING",
            quantity_inspected=10,
        )

    def test_inspection_form_limits_jobs_and_positive_quantity(self):
        cancelled_job = ProductionJob.objects.create(
            product=self.product,
            status="CANCELLED",
            quantity_to_produce=2,
            created_by=self.employee,
        )
        form = QualityInspectionForm()
        self.assertIn(self.job, form.fields["production_job"].queryset)
        self.assertNotIn(cancelled_job, form.fields["production_job"].queryset)
        invalid = QualityInspectionForm(
            data={
                "production_job": self.job.pk,
                "inspection_type": "FINAL",
                "inspector": self.employee.pk,
                "quantity_inspected": 0,
                "remarks": "",
            }
        )
        self.assertFalse(invalid.is_valid())
        self.assertIn("quantity_inspected", invalid.errors)

    def test_result_quantities_must_account_for_all_inspected_units(self):
        form = QualityInspectionResultForm(
            data={
                "result": "FAILED",
                "score": 70,
                "quantity_inspected": 10,
                "quantity_passed": 7,
                "quantity_failed": 2,
                "inspector": self.employee.pk,
                "remarks": "One unit is unaccounted for.",
            },
            instance=self.inspection,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Passed and failed quantities must equal", str(form.errors))

    def test_recorded_result_cannot_be_overwritten(self):
        self.inspection.result = "FAILED"
        self.inspection.quantity_passed = 8
        self.inspection.quantity_failed = 2
        self.inspection.save()
        with self.assertRaisesMessage(
            ValidationError,
            "A recorded inspection result cannot be changed.",
        ):
            QualityService.record_result(
                inspection=self.inspection,
                result="PASSED",
                score=100,
                quantity_inspected=10,
                quantity_passed=10,
                quantity_failed=0,
                inspector=self.employee,
            )

    def test_defect_quantity_cannot_exceed_failed_quantity(self):
        self.inspection.result = "FAILED"
        self.inspection.quantity_passed = 8
        self.inspection.quantity_failed = 2
        self.inspection.save()
        form = ProductionDefectForm(
            data={
                "defect_type": "ASSEMBLY",
                "severity": "MAJOR",
                "description": "Loose joints",
                "affected_quantity": 3,
                "root_cause": "",
                "corrective_action": "",
                "rework_required": True,
            },
            inspection=self.inspection,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("affected_quantity", form.errors)

    def test_defect_cannot_have_two_active_rework_orders(self):
        self.inspection.result = "FAILED"
        self.inspection.quantity_passed = 8
        self.inspection.quantity_failed = 2
        self.inspection.save()
        defect = ProductionDefect.objects.create(
            inspection=self.inspection,
            production_job=self.job,
            defect_type="ASSEMBLY",
            severity="MAJOR",
            description="Loose joints",
            affected_quantity=2,
            status="REWORK_REQUIRED",
        )
        ReworkOrder.objects.create(
            production_job=self.job,
            defect=defect,
            assigned_to=self.employee,
            status="ASSIGNED",
            instructions="Repair joints",
            estimated_hours=Decimal("2.00"),
        )
        with self.assertRaisesMessage(
            ValidationError,
            "already has an active rework order",
        ):
            QualityService.assign_rework(
                defect=defect,
                assigned_to=self.employee,
                instructions="Duplicate work",
                estimated_hours=Decimal("1.00"),
                created_by=self.employee,
            )

    def test_in_process_inspection_cannot_approve_finished_goods(self):
        self.inspection.inspection_type = "IN_PROCESS"
        self.inspection.result = "PASSED"
        self.inspection.quantity_passed = 10
        self.inspection.quantity_failed = 0
        self.inspection.save()
        with self.assertRaisesMessage(
            ValidationError,
            "Only a final inspection or re-inspection",
        ):
            QualityService.approve_finished_goods(
                inspection=self.inspection,
                approved_by=self.employee,
            )

    def test_rework_complete_and_verify_forms_open_on_get(self):
        self.inspection.result = "FAILED"
        self.inspection.quantity_passed = 8
        self.inspection.quantity_failed = 2
        self.inspection.save()
        defect = ProductionDefect.objects.create(
            inspection=self.inspection,
            production_job=self.job,
            defect_type="ASSEMBLY",
            severity="MAJOR",
            description="Loose joints",
            affected_quantity=2,
            status="UNDER_REWORK",
        )
        rework = ReworkOrder.objects.create(
            production_job=self.job,
            defect=defect,
            assigned_to=self.employee,
            status="IN_PROGRESS",
            instructions="Repair joints",
            estimated_hours=Decimal("2.00"),
        )
        response = self.client.get(
            reverse("furniture:rework_order_complete", args=[rework.pk])
        )
        self.assertEqual(response.status_code, 200)

        rework.status = "COMPLETED"
        rework.save(update_fields=["status"])
        response = self.client.get(
            reverse("furniture:rework_order_verify", args=[rework.pk])
        )
        self.assertEqual(response.status_code, 200)
