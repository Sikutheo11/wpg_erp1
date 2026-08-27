from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from Employee.models import Employee
from inventory.models import Product

from .models import ProductionJob, ProductionSettings, Quotation


class FurnitureClosureUxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="closure-admin@example.com",
            username="closure-admin",
            first_name="Closure",
            last_name="Admin",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)
        self.employee = Employee.objects.create(
            user=self.user,
            national_id="CLOSURE-001",
            emergency_contact="0788000040",
        )
        self.product = Product.objects.create(
            name="Closure Desk",
            product_code="CLOSURE-DESK-001",
            business_unit="FURNITURE",
        )
        self.job = ProductionJob.objects.create(
            product=self.product,
            status="IN_PRODUCTION",
            quantity_to_produce=5,
            created_by=self.employee,
        )

    def test_production_job_list_uses_current_jobs_not_legacy_orders(self):
        response = self.client.get(reverse("furniture:production_job_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Closure Desk")
        self.assertContains(response, f"#{self.job.pk}")
        self.assertNotContains(response, "approve_order")
        self.assertNotContains(response, "assign_order")

    def test_job_detail_prefills_task_with_correct_query_parameter(self):
        response = self.client.get(
            reverse("furniture:production_job_detail", args=[self.job.pk])
        )
        self.assertEqual(response.status_code, 200)
        expected = f'{reverse("furniture:production_task_create")}?job={self.job.pk}'
        self.assertContains(response, expected)

    @patch("furniture.views.ProductionCostService.job_cost_summary")
    def test_job_detail_uses_configured_cost_settings(self, job_cost_summary):
        job_cost_summary.return_value = {
            "has_quotation": False,
            "is_profitable": False,
            "material_cost": Decimal("0.00"),
            "labour_cost": Decimal("0.00"),
            "machine_cost": Decimal("0.00"),
            "actual_total_cost": Decimal("0.00"),
            "cost_per_unit": Decimal("0.00"),
            "expected_revenue": Decimal("0.00"),
            "actual_profit": Decimal("0.00"),
            "profit_margin": Decimal("0.00"),
            "completion_rate": Decimal("0.00"),
        }
        ProductionSettings.objects.all().delete()
        ProductionSettings.objects.create(
            overhead_rate=Decimal("17.00"),
            wastage_rate=Decimal("6.00"),
            default_transport_cost=Decimal("12000.00"),
            default_other_cost=Decimal("3000.00"),
        )
        response = self.client.get(
            reverse("furniture:production_job_detail", args=[self.job.pk])
        )
        self.assertEqual(response.status_code, 200)
        job_cost_summary.assert_called_once_with(
            production_job=self.job,
            overhead_rate=Decimal("17.00"),
            wastage_rate=Decimal("6.00"),
            transport_cost=Decimal("12000.00"),
            other_cost=Decimal("3000.00"),
        )

    def test_submitted_quotation_review_opens_on_get(self):
        quotation = Quotation.objects.create(
            production_job=self.job,
            prepared_by=self.employee,
            status="SUBMITTED",
            selling_price=Decimal("100000.00"),
        )
        response = self.client.get(
            reverse("furniture:approve_quotation", args=[quotation.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Review Quotation #{quotation.pk}")
