from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from Employee.models import Employee
from inventory.models import Product, StockMovement, Warehouse

from .forms import ProductionOutputForm, ProductionTaskForm
from .models import ProductionJob, ProductionOutput, ProductionTask
from .services import ProductionTaskService


class FurnitureOutputTaskUxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="output-task-admin@example.com",
            username="output-task-admin",
            first_name="Output",
            last_name="Admin",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)

        self.employee = Employee.objects.create(
            user=self.user,
            national_id="OUTPUT-TASK-001",
            emergency_contact="0788000010",
        )

        self.product = Product.objects.create(
            name="Finished Desk",
            product_code="FIN-DESK-001",
            business_unit="FURNITURE",
            standard_cost=Decimal("45000.00"),
        )

        self.job = ProductionJob.objects.create(
            product=self.product,
            status="IN_PRODUCTION",
            quantity_to_produce=10,
            created_by=self.employee,
        )

        self.warehouse = Warehouse.objects.create(
            name="Finished Goods Store",
            warehouse_type="FINISHED_GOODS",
            business_unit="FURNITURE",
        )

    def test_output_form_uses_job_product_without_inventory_warehouse(self):
        form = ProductionOutputForm(
            production_job=self.job
        )

        self.assertNotIn(
            "product",
            form.fields,
        )

        self.assertNotIn(
            "warehouse",
            form.fields,
        )

        self.assertEqual(
            set(form.fields),
            {
                "quantity_produced",
                "image",
            },
        )

    def test_output_cannot_exceed_remaining_job_quantity(self):
        ProductionOutput.objects.create(
            production_job=self.job,
            product=self.product,
            quantity_produced=8,
            produced_by=self.employee,
        )

        form = ProductionOutputForm(
            data={
                "quantity_produced": 3,
            },
            production_job=self.job,
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "quantity_produced",
            form.errors,
        )

    def test_output_is_recorded_without_receiving_inventory_stock(self):
        response = self.client.post(
            reverse(
                "furniture:add_output",
                args=[self.job.pk],
            ),
            {
                "quantity_produced": 4,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        output = ProductionOutput.objects.get(
            production_job=self.job
        )

        self.assertEqual(
            output.quantity_produced,
            4,
        )

        self.assertIsNone(
            output.inventory_movement_id
        )

        self.assertEqual(
            StockMovement.objects.filter(
                product=self.product,
                reference_type="PRODUCTION_JOB",
                reference_id=str(self.job.pk),
            ).count(),
            0,
        )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.status,
            "IN_PRODUCTION",
        )

    def test_full_output_moves_job_to_quality_check_without_stock_receipt(self):
        response = self.client.post(
            reverse(
                "furniture:add_output",
                args=[self.job.pk],
            ),
            {
                "quantity_produced": 10,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.job.refresh_from_db()

        output = ProductionOutput.objects.get(
            production_job=self.job
        )

        self.assertEqual(
            self.job.status,
            "QUALITY_CHECK",
        )

        self.assertIsNone(
            output.inventory_movement_id
        )

        self.assertFalse(
            StockMovement.objects.filter(
                product=self.product,
                reference_type="PRODUCTION_JOB",
                reference_id=str(self.job.pk),
            ).exists()
        )

    def test_started_task_locks_job_sequence_and_assignment_in_edit_form(self):
        task = ProductionTask.objects.create(
            production_job=self.job,
            name="Assembly",
            sequence=1,
            status="IN_PROGRESS",
            assigned_to=self.employee,
        )

        form = ProductionTaskForm(
            instance=task
        )

        self.assertTrue(
            form.fields["production_job"].disabled
        )

        self.assertTrue(
            form.fields["sequence"].disabled
        )

        self.assertTrue(
            form.fields["assigned_to"].disabled
        )

    def test_pending_task_cannot_be_completed_directly(self):
        task = ProductionTask.objects.create(
            production_job=self.job,
            name="Cutting",
            sequence=1,
            status="PENDING",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Only an active, paused or blocked task can be completed.",
        ):
            ProductionTaskService.complete_task(
                task,
                employee=self.employee,
            )

    def test_active_task_completes_without_name_error(self):
        task = ProductionTask.objects.create(
            production_job=self.job,
            name="Finishing",
            sequence=1,
            status="IN_PROGRESS",
        )

        ProductionTaskService.complete_task(
            task,
            employee=self.employee,
        )

        task.refresh_from_db()

        self.assertEqual(
            task.status,
            "COMPLETED",
        )

        self.assertEqual(
            task.progress_percentage,
            100,
        )
