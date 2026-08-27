from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .lifecycle_guards import ProductionJobTransitionGuard


class ProductionJobTransitionGuardTests(SimpleTestCase):
    def job(self, status="MATERIAL_RESERVED"):
        return type("Job", (), {"status": status})()

    @patch("furniture.lifecycle_guards.ProductionJobLifecycleEvidence.build")
    def test_start_blocks_unapproved_plan(self, evidence):
        evidence.return_value = {
            "order": {"exists": True, "authorized": True},
            "plan": {"approved": False},
            "funding": {"ready": True, "message": ""},
            "materials": {"ready": True},
        }
        with self.assertRaisesMessage(ValidationError, "approved Production Plan"):
            ProductionJobTransitionGuard.assert_can_start_production(self.job())

    @patch("furniture.lifecycle_guards.ProductionJobLifecycleEvidence.build")
    def test_start_blocks_funding_gap(self, evidence):
        evidence.return_value = {
            "order": {"exists": True, "authorized": True},
            "plan": {"approved": True},
            "funding": {
                "ready": False,
                "message": "Funding gap remains 2,000,000 RWF.",
            },
            "materials": {"ready": True},
        }
        with self.assertRaisesMessage(ValidationError, "Funding gap remains"):
            ProductionJobTransitionGuard.assert_can_start_production(self.job())

    def test_direct_finished_goods_transition_is_disabled(self):
        with self.assertRaisesMessage(ValidationError, "Direct QUALITY CHECK"):
            ProductionJobTransitionGuard.assert_legacy_finished_goods_transition_disabled(
                self.job("QUALITY_CHECK")
            )

    @patch("furniture.lifecycle_guards.ProductionJobLifecycleEvidence.build")
    def test_delivery_blocks_before_inventory_release(self, evidence):
        evidence.return_value = {
            "inventory": {"all_output_released": False},
            "order": {"exists": True},
            "delivery": {"complete": False},
        }
        with self.assertRaisesMessage(ValidationError, "released to Inventory"):
            ProductionJobTransitionGuard.assert_can_mark_delivered(
                self.job("FINISHED_GOODS")
            )
