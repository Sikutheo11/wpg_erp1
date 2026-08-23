from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from .models import Counterparty, ObligationLine, Payable, Receivable
from .services import DebtReportService


class ObligationWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="obligation-user",
            email="obligation@example.com",
            first_name="Obligation",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )
        group = Group.objects.create(name="Obligation Managers")
        group.permissions.add(*Permission.objects.filter(content_type__app_label="finance", codename__in=["add_payable", "add_receivable", "view_debtrecord"]))
        self.user.groups.add(group)
        self.client.force_login(self.user)
        self.party = Counterparty.objects.create(name="Example Partner", phone="0788123456")

    def _post(self, url_name, reference):
        return self.client.post(reverse(url_name), {
            "counterparty": self.party.pk, "reference" if url_name.endswith("payable_create") else "invoice_number": reference,
            "business_unit": "GENERAL", "transaction_date": "2026-08-23", "due_date": "2026-09-23", "notes": "Test",
            "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0", "lines-MIN_NUM_FORMS": "1", "lines-MAX_NUM_FORMS": "1000",
            "lines-0-item_type": "OTHER", "lines-0-description": "Professional service", "lines-0-quantity": "2", "lines-0-unit": "day", "lines-0-unit_price": "15000",
        })

    def test_payable_total_is_calculated_from_lines(self):
        response = self._post("finance:payable_create", "PAY-001")
        self.assertEqual(response.status_code, 302)
        payable = Payable.objects.get(reference="PAY-001")
        self.assertEqual(payable.total_amount, 30000)
        self.assertEqual(payable.lines.count(), 1)
        self.party.refresh_from_db()
        self.assertTrue(self.party.is_supplier)

    def test_receivable_total_is_calculated_from_lines(self):
        response = self._post("finance:receivable_create", "REC-001")
        self.assertEqual(response.status_code, 302)
        receivable = Receivable.objects.get(invoice_number="REC-001")
        self.assertEqual(receivable.total_amount, 30000)
        self.party.refresh_from_db()
        self.assertTrue(self.party.is_customer)

    def test_unified_report_contains_both_directions(self):
        self._post("finance:payable_create", "PAY-002")
        self._post("finance:receivable_create", "REC-002")
        report = DebtReportService.build({})
        self.assertEqual({row["direction"] for row in report["rows"]}, {"PAYABLE", "RECEIVABLE"})

    def test_csv_export_uses_same_report(self):
        self._post("finance:payable_create", "PAY-CSV")
        response = self.client.get(reverse("finance:debt_report_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PAY-CSV", response.content)
