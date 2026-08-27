from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from Employee.models import Employee
from inventory.models import Asset, Product, RawMaterial, Warehouse

from .forms import ProductionLabourForm, ProductionMachineForm, ProductionMaterialForm
from .models import ProductionJob, ProductionLabour, ProductionMachine, ProductionSettings


class FurnitureResourceFormUxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="resource-admin@example.com",
            username="resource-admin",
            first_name="Resource",
            last_name="Admin",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)
        self.employee = Employee.objects.create(
            user=self.user,
            national_id="RESOURCE-001",
            emergency_contact="0788000000",
            hourly_rate=Decimal("2500.00"),
        )
        self.product = Product.objects.create(
            name="Test Furniture",
            product_code="FURN-RESOURCE-001",
            business_unit="FURNITURE",
        )
        self.job = ProductionJob.objects.create(
            product=self.product,
            status="IN_PRODUCTION",
            quantity_to_produce=1,
            created_by=self.employee,
        )
        self.material = RawMaterial.objects.create(
            name="Timber",
            code="RAW-TIMBER-001",
            unit="pcs",
            unit_cost=Decimal("5000.00"),
        )
        self.warehouse = Warehouse.objects.create(
            name="Raw Material Store",
            warehouse_type="RAW_MATERIAL",
            business_unit="FURNITURE",
        )
        self.machine = Asset.objects.create(
            name="Panel Saw",
            asset_type="machine",
            purchase_cost=Decimal("500000.00"),
            purchase_date=date(2026, 1, 1),
        )

    def test_forms_request_only_operational_inputs(self):
        self.assertEqual(
            list(ProductionMaterialForm().fields),
            ["raw_material", "quantity_used", "warehouse"],
        )
        self.assertEqual(
            list(ProductionLabourForm().fields),
            ["employee", "hours_worked"],
        )
        self.assertEqual(
            list(ProductionMachineForm().fields),
            ["asset", "hours_used"],
        )

    def test_inactive_resources_are_not_selectable(self):
        inactive_user = get_user_model().objects.create_user(
            email="inactive@example.com",
            username="inactive-resource",
            first_name="Inactive",
            last_name="Resource",
            password="Strong-Test-Password-2026!",
        )
        inactive_employee = Employee.objects.create(
            user=inactive_user,
            national_id="RESOURCE-002",
            emergency_contact="0788000001",
            is_active=False,
        )
        inactive_machine = Asset.objects.create(
            name="Retired Saw",
            asset_type="machine",
            purchase_cost=Decimal("1000.00"),
            purchase_date=date(2025, 1, 1),
            status="inactive",
        )

        self.assertNotIn(inactive_employee, ProductionLabourForm().fields["employee"].queryset)
        self.assertNotIn(inactive_machine, ProductionMachineForm().fields["asset"].queryset)

    @patch("furniture.views.FurnitureInventoryService.record_material_usage")
    def test_material_submission_issues_stock_through_inventory_service(self, record_usage):
        response = self.client.post(
            reverse("furniture:add_material", args=[self.job.pk]),
            {
                "raw_material": self.material.pk,
                "quantity_used": "3.00",
                "warehouse": self.warehouse.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        record_usage.assert_called_once_with(
            production_job=self.job,
            raw_material=self.material,
            quantity=Decimal("3.00"),
            warehouse=self.warehouse,
            performed_by=self.user,
        )

    def test_labour_rate_is_derived_from_employee(self):
        response = self.client.post(
            reverse("furniture:add_labour", args=[self.job.pk]),
            {"employee": self.employee.pk, "hours_worked": "2.50"},
        )

        self.assertEqual(response.status_code, 302)
        labour = ProductionLabour.objects.get(production_job=self.job)
        self.assertEqual(labour.hourly_rate, Decimal("2500.00"))

    def test_machine_rate_is_derived_from_settings(self):
        ProductionSettings.objects.create(
            default_machine_hourly_cost=Decimal("3200.00"),
        )
        response = self.client.post(
            reverse("furniture:add_machine", args=[self.job.pk]),
            {"asset": self.machine.pk, "hours_used": "1.50"},
        )

        self.assertEqual(response.status_code, 302)
        usage = ProductionMachine.objects.get(production_job=self.job)
        self.assertEqual(usage.hourly_cost, Decimal("3200.00"))

    def test_resources_cannot_be_recorded_before_production_starts(self):
        self.job.status = "APPROVED"
        self.job.save(update_fields=["status"])

        response = self.client.get(reverse("furniture:add_labour", args=[self.job.pk]))

        self.assertRedirects(
            response,
            reverse("furniture:production_job_detail", args=[self.job.pk]),
            fetch_redirect_response=False,
        )
