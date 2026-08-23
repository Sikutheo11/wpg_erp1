from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from .models import Counterparty, ObligationItemGroup, ObligationItemType, Payable, Receivable
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
        self.group, _ = ObligationItemGroup.objects.get_or_create(
            business_unit="FURNITURE", name="Furniture Products"
        )
        self.item, _ = ObligationItemType.objects.get_or_create(
            item_group=self.group, name="Dining Chair", defaults={"default_unit": "piece"}
        )

    def _post(self, url_name, reference=None):
        return self.client.post(reverse(url_name), {
            "counterparty": self.party.pk,
            "business_unit": "FURNITURE", "item_group": self.group.pk,
            "transaction_date": "2026-08-23",
            "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0", "lines-MIN_NUM_FORMS": "1", "lines-MAX_NUM_FORMS": "1000",
            "lines-0-catalog_item": self.item.pk, "lines-0-quantity": "2", "lines-0-unit_price": "15000",
        })

    def test_payable_total_is_calculated_from_lines(self):
        response = self._post("finance:payable_create", "PAY-001")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("finance:payable_list"))
        payable = Payable.objects.get()
        self.assertTrue(payable.reference.startswith("PAY-20260823-"))
        self.assertEqual(str(payable.due_date), "2026-09-22")
        self.assertEqual(payable.total_amount, 30000)
        self.assertEqual(payable.lines.count(), 1)
        self.party.refresh_from_db()
        self.assertTrue(self.party.is_supplier)

    def test_receivable_total_is_calculated_from_lines(self):
        response = self._post("finance:receivable_create", "REC-001")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("finance:receivable_list"))
        receivable = Receivable.objects.get()
        self.assertTrue(receivable.invoice_number.startswith("REC-20260823-"))
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
        self.assertIn(b"PAY-20260823-", response.content)

    def test_form_only_exposes_approved_header_and_line_fields(self):
        from .forms import PayableForm, ObligationLineForm
        self.assertEqual(list(PayableForm().fields), ["counterparty", "business_unit", "item_group", "transaction_date"])
        self.assertEqual(list(ObligationLineForm().fields), ["catalog_item", "quantity", "unit_price"])

    def test_catalog_json_is_filtered_by_business_unit_and_group(self):
        other, _ = ObligationItemGroup.objects.get_or_create(business_unit="AGRICULTURE", name="Poultry Birds")
        ObligationItemType.objects.get_or_create(item_group=other, name="Broiler")
        groups = self.client.get(reverse("finance:obligation_item_groups_json"), {"business_unit": "FURNITURE"}).json()["results"]
        self.assertIn("Furniture Products", [row["name"] for row in groups])
        items = self.client.get(reverse("finance:obligation_item_types_json"), {"item_group": self.group.pk}).json()["results"]
        self.assertIn("Dining Chair", [row["name"] for row in items])

    def test_catalog_items_json_accepts_empty_group(self):
        response = self.client.get(
            reverse("finance:obligation_item_types_json"),
            {"item_group": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": []})

    def test_missing_catalog_item_returns_form_error_instead_of_crashing(self):
        response = self.client.post(reverse("finance:payable_create"), {
            "counterparty": self.party.pk,
            "business_unit": "FURNITURE",
            "item_group": self.group.pk,
            "transaction_date": "2026-08-23",
            "lines-TOTAL_FORMS": "1",
            "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "1",
            "lines-MAX_NUM_FORMS": "1000",
            "lines-0-catalog_item": "",
            "lines-0-quantity": "2",
            "lines-0-unit_price": "15000",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(Payable.objects.count(), 0)

    def test_receivable_list_links_to_new_catalog_form(self):
        view_permission = Permission.objects.get(
            content_type__app_label="finance", codename="view_receivable"
        )
        self.user.groups.first().permissions.add(view_permission)
        response = self.client.get(reverse("finance:receivable_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("finance:receivable_create"))
        self.assertContains(response, "New Receivable")

    def test_payable_list_has_responsive_mobile_cards(self):
        view_permission = Permission.objects.get(
            content_type__app_label="finance", codename="view_payable"
        )
        self.user.groups.first().permissions.add(view_permission)
        response = self.client.get(reverse("finance:payable_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mobile-register")
        self.assertContains(response, "desktop-register")

    def test_missing_counterparty_returns_form_error_instead_of_crashing(self):
        response = self.client.post(reverse("finance:receivable_create"), {
            "counterparty": "",
            "business_unit": "FURNITURE",
            "item_group": self.group.pk,
            "transaction_date": "2026-08-23",
            "lines-TOTAL_FORMS": "1",
            "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "1",
            "lines-MAX_NUM_FORMS": "1000",
            "lines-0-catalog_item": self.item.pk,
            "lines-0-quantity": "2",
            "lines-0-unit_price": "15000",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertEqual(Receivable.objects.count(), 0)
