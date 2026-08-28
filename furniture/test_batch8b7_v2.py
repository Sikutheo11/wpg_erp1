from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .lifecycle_guards import ProductionJobTransitionGuard
from .profitability_service import (
    FurnitureProfitabilityReconciliationService,
)


class FurnitureBatch8B7V2Tests(SimpleTestCase):
    def _evidence(self):
        return {
            "order": {"exists": True},
            "delivery": {"complete": True},
            "inventory": {"all_output_released": True},
            "finance": {
                "payment_complete": True,
                "investment_status": None,
            },
        }

    def test_profitability_does_not_double_count_cost(self):
        order = SimpleNamespace(
            total_amount=Decimal("1000.00")
        )
        job = SimpleNamespace(pk=1, order=order)

        with patch(
            "furniture.services.costing_service."
            "ProductionCostService.total_cost",
            return_value=Decimal("600.00"),
        ):
            result = (
                FurnitureProfitabilityReconciliationService.build(
                    job,
                    evidence=self._evidence(),
                )
            )

        self.assertEqual(
            result["actual_revenue"],
            Decimal("1000.00"),
        )
        self.assertEqual(
            result["actual_cost"],
            Decimal("600.00"),
        )
        self.assertEqual(
            result["actual_profit"],
            Decimal("400.00"),
        )

    @patch(
        "furniture.lifecycle_guards."
        "FurnitureProfitabilityReconciliationService.build"
    )
    @patch(
        "furniture.lifecycle_guards."
        "ProductionJobLifecycleEvidence.build"
    )
    def test_close_blocks_unreconciled_profitability(
        self,
        evidence,
        profitability,
    ):
        job = SimpleNamespace(status="FINANCE")
        evidence.return_value = self._evidence()
        profitability.return_value = {
            "reconciliation_ready": False,
        }

        with self.assertRaisesMessage(
            ValidationError,
            "profitability reconciliation",
        ):
            ProductionJobTransitionGuard.assert_can_close(job)
