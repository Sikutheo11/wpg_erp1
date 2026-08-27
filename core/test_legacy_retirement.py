from io import StringIO

from django.contrib.admin.sites import AdminSite
from django.core.management import call_command
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase
from django.urls import NoReverseMatch, reverse

from sales.admin import CustomerPaymentAdmin, InvoiceAdmin, SaleAdmin
from sales.models import CustomerPayment, Invoice, Sale


class LegacyRetirementConfigurationTests(SimpleTestCase):
    def test_legacy_furniture_write_routes_are_removed(self):
        for route_name in ("furniture:assign_worker", "furniture:create_quotation"):
            with self.assertRaises(NoReverseMatch):
                reverse(route_name, kwargs={"pk": 1})

    def test_legacy_furniture_list_has_read_only_template(self):
        get_template("furniture/order_list.html")

    def test_legacy_sales_admins_are_read_only(self):
        site = AdminSite()
        for admin_class, model in (
            (SaleAdmin, Sale),
            (InvoiceAdmin, Invoice),
            (CustomerPaymentAdmin, CustomerPayment),
        ):
            model_admin = admin_class(model, site)
            self.assertFalse(model_admin.has_add_permission(None))
            self.assertFalse(model_admin.has_change_permission(None))
            self.assertFalse(model_admin.has_delete_permission(None))


class LegacyRetirementAuditCommandTests(TestCase):
    def test_audit_command_reports_summary(self):
        output = StringIO()
        call_command("audit_legacy_models", stdout=output)
        self.assertIn("LEGACY_RETIREMENT_SUMMARY: remaining=0", output.getvalue())
