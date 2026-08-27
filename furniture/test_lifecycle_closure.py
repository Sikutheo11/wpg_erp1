from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.urls import reverse

from .lifecycle_guards import ProductionJobTransitionGuard
from .models import ProductionJob


class ProductionJobLifecycleClosureTests(SimpleTestCase):
    def test_production_job_status_contains_finance(self):
        codes = {value for value, _label in ProductionJob.STATUS}
        self.assertIn("FINANCE", codes)
        self.assertIn("CLOSED", codes)

    def test_closure_urls_reverse(self):
        self.assertEqual(
            reverse("furniture:production_job_confirm_delivery", args=[9]),
            "/furniture/production-jobs/9/confirm-delivery/",
        )
        self.assertEqual(
            reverse("furniture:production_job_move_to_finance", args=[9]),
            "/furniture/production-jobs/9/move-to-finance/",
        )
        self.assertEqual(
            reverse("furniture:production_job_close", args=[9]),
            "/furniture/production-jobs/9/close/",
        )

    @patch("furniture.lifecycle_guards.ProductionJobLifecycleEvidence.build")
    def test_close_blocks_unpaid_customer(self, evidence):
        job = type("Job", (), {"status": "FINANCE"})()
        evidence.return_value = {
            "order": {"exists": True},
            "delivery": {"complete": True},
            "finance": {"payment_complete": False, "investment_status": None},
        }
        with self.assertRaisesMessage(ValidationError, "Customer payment"):
            ProductionJobTransitionGuard.assert_can_close(job)

    @patch("furniture.lifecycle_guards.ProductionJobLifecycleEvidence.build")
    def test_close_blocks_open_investor_settlement(self, evidence):
        job = type("Job", (), {"status": "FINANCE"})()
        evidence.return_value = {
            "order": {"exists": True},
            "delivery": {"complete": True},
            "finance": {"payment_complete": True, "investment_status": "SETTLEMENT"},
        }
        with self.assertRaisesMessage(ValidationError, "Job Funding record"):
            ProductionJobTransitionGuard.assert_can_close(job)
