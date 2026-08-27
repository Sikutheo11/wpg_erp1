from django.test import TestCase

from inventory.models import Product

from .lifecycle_evidence import ProductionJobLifecycleEvidence
from .models import ProductionJob, ProductionOutput


class ProductionJobLifecycleEvidenceTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Lifecycle Evidence Product",
            product_code="LIFE-EVIDENCE-001",
            business_unit="FURNITURE",
        )
        self.job = ProductionJob.objects.create(
            product=self.product,
            job_type="RESTOCK",
            status="IN_PRODUCTION",
            quantity_to_produce=5,
        )

    def test_job_without_order_does_not_require_external_funding(self):
        evidence = ProductionJobLifecycleEvidence.build(self.job)
        self.assertFalse(evidence["order"]["exists"])
        self.assertFalse(evidence["funding"]["exists"])
        self.assertTrue(evidence["funding"]["ready"])

    def test_materials_not_ready_when_no_reservations_exist(self):
        evidence = ProductionJobLifecycleEvidence.build(self.job)
        self.assertFalse(evidence["materials"]["ready"])

    def test_output_is_not_inventory_until_released(self):
        ProductionOutput.objects.create(
            production_job=self.job,
            product=self.product,
            quantity_produced=5,
        )
        evidence = ProductionJobLifecycleEvidence.build(self.job)
        self.assertTrue(evidence["production"]["output_complete"])
        self.assertFalse(evidence["inventory"]["all_output_released"])
