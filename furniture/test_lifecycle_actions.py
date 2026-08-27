from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import reverse

from .lifecycle_actions import ProductionJobLifecycleActions


class ProductionJobLifecycleActionsTests(SimpleTestCase):
    def make_job(self, status="IN_PRODUCTION", order=None, product_id=1):
        return SimpleNamespace(pk=11, status=status, order=order, product_id=product_id)

    def evidence(self):
        return {
            "plan": {"latest": None},
            "funding": {"ready": True, "message": "Funding is sufficient."},
            "delivery": {"complete": False},
            "finance": {"payment_complete": False},
        }

    def test_product_action_uses_furniture_product_detail(self):
        actions = ProductionJobLifecycleActions.build(
            job=self.make_job(), evidence=self.evidence()
        )
        action = next(x for x in actions if x["code"] == "PRODUCT")
        self.assertEqual(
            action["url"],
            reverse("furniture:furniture_product_detail", args=[1]),
        )

    def test_in_production_exposes_record_output(self):
        actions = ProductionJobLifecycleActions.build(
            job=self.make_job("IN_PRODUCTION"), evidence=self.evidence()
        )
        action = next(x for x in actions if x["code"] == "OUTPUT")
        self.assertEqual(
            action["url"],
            reverse("furniture:add_output", args=[11]),
        )

    def test_quality_check_without_inspection_exposes_create_inspection(self):
        actions = ProductionJobLifecycleActions.build(
            job=self.make_job("QUALITY_CHECK"),
            evidence=self.evidence(),
            inspection=None,
        )
        action = next(x for x in actions if x["code"] == "QUALITY")
        self.assertEqual(
            action["url"],
            reverse("furniture:quality_inspection_create", args=[11]),
        )
