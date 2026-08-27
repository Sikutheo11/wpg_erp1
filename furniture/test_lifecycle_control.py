from types import SimpleNamespace
from django.test import SimpleTestCase
from .lifecycle_control import ProductionJobLifecycleControl

class ProductionJobLifecycleControlTests(SimpleTestCase):
    def make_job(self, status):
        return SimpleNamespace(status=status, get_status_display=lambda: status.replace("_", " ").title())

    def test_in_production_is_current_stage(self):
        c = ProductionJobLifecycleControl.build(job=self.make_job("IN_PRODUCTION"))
        self.assertEqual(c["current_code"], "IN_PRODUCTION")
        self.assertEqual([x for x in c["stages"] if x["state"] == "CURRENT"][0]["code"], "IN_PRODUCTION")

    def test_quality_without_inspection_requests_inspection(self):
        c = ProductionJobLifecycleControl.build(job=self.make_job("QUALITY_CHECK"))
        self.assertEqual(c["next_action"]["title"], "Perform final quality inspection")

    def test_failed_quality_requests_rework(self):
        i = SimpleNamespace(result="FAILED", approved_by_id=None)
        c = ProductionJobLifecycleControl.build(job=self.make_job("QUALITY_CHECK"), inspection=i)
        self.assertEqual(c["next_action"]["title"], "Resolve quality failure / rework")

    def test_passed_unapproved_quality_requests_approval(self):
        i = SimpleNamespace(result="PASSED", approved_by_id=None)
        c = ProductionJobLifecycleControl.build(job=self.make_job("QUALITY_CHECK"), inspection=i)
        self.assertEqual(c["next_action"]["title"], "Approve final quality inspection")

    def test_ready_job_requests_inventory_release(self):
        c = ProductionJobLifecycleControl.build(job=self.make_job("READY_FOR_FINISHED_GOODS"))
        self.assertEqual(c["next_action"]["title"], "Release to Inventory")

    def test_finished_goods_requests_delivery(self):
        c = ProductionJobLifecycleControl.build(job=self.make_job("FINISHED_GOODS"))
        self.assertEqual(c["next_action"]["title"], "Prepare delivery")
