from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from finance.models import Counterparty


class CounterpartyViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            username="finance-tester",
            email="finance.tester@wisdompalacegroup.com",
            first_name="Finance",
            last_name="Tester",
            password="Strong-Test-Password-2026",
        )

        finance_group = Group.objects.create(
            name="Counterparty Test Users",
        )
        finance_group.permissions.add(
            Permission.objects.get(
                content_type__app_label="finance",
                codename="view_counterparty",
            ),
            Permission.objects.get(
                content_type__app_label="finance",
                codename="add_counterparty",
            ),
        )
        self.user.groups.add(finance_group)

        self.client.force_login(self.user)

    def test_phone_lookup_page_requires_login(self):
        self.client.logout()

        response = self.client.get(
            reverse(
                "finance:counterparty_phone_lookup"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_new_phone_redirects_to_creation_form(self):
        response = self.client.post(
            reverse(
                "finance:counterparty_phone_lookup"
            ),
            {
                "phone": "0788123456",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "finance:counterparty_create"
            ),
        )

        self.assertEqual(
            self.client.session[
                "counterparty_pending_phone"
            ],
            "+250788123456",
        )

    def test_existing_phone_redirects_to_existing_account(self):
        counterparty = Counterparty.objects.create(
            name="Existing Person",
            phone="0788123456",
            is_customer=True,
        )

        response = self.client.post(
            reverse(
                "finance:counterparty_phone_lookup"
            ),
            {
                "phone": "+250 788 123 456",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "finance:counterparty_detail",
                kwargs={
                    "pk": counterparty.pk,
                },
            ),
        )

        self.assertEqual(
            Counterparty.objects.count(),
            1,
        )

    def test_creation_page_requires_prior_phone_lookup(self):
        response = self.client.get(
            reverse(
                "finance:counterparty_create"
            ),
        )

        self.assertRedirects(
            response,
            reverse(
                "finance:counterparty_phone_lookup"
            ),
        )

    def test_new_counterparty_can_be_created_after_lookup(self):
        lookup_response = self.client.post(
            reverse(
                "finance:counterparty_phone_lookup"
            ),
            {
                "phone": "0788123456",
            },
        )

        self.assertEqual(
            lookup_response.status_code,
            302,
        )

        response = self.client.post(
            reverse(
                "finance:counterparty_create"
            ),
            {
                "phone": "+250788123456",
                "party_type": "INDIVIDUAL",
                "name": "New Customer",
                "relationship": "CUSTOMER",
                "email": "",
                "address": "Karongi",
                "tax_number": "",
                "bank_name": "",
                "bank_account_name": "",
                "bank_account_number": "",
            },
        )

        counterparty = Counterparty.objects.get()

        self.assertRedirects(
            response,
            reverse(
                "finance:counterparty_detail",
                kwargs={
                    "pk": counterparty.pk,
                },
            ),
        )

        self.assertEqual(
            counterparty.phone,
            "+250788123456",
        )
        self.assertTrue(
            counterparty.is_customer,
        )
        self.assertFalse(
            counterparty.is_supplier,
        )
        self.assertNotIn(
            "counterparty_pending_phone",
            self.client.session,
        )

    def test_duplicate_bank_account_is_not_created(self):
        Counterparty.objects.create(
            name="Existing Account Holder",
            phone="0788111111",
            bank_name="Bank of Kigali",
            bank_account_number="0012 3456 7890",
        )

        self.client.post(
            reverse(
                "finance:counterparty_phone_lookup"
            ),
            {
                "phone": "0788222222",
            },
        )

        response = self.client.post(
            reverse(
                "finance:counterparty_create"
            ),
            {
                "phone": "+250788222222",
                "party_type": "INDIVIDUAL",
                "name": "Duplicate Account Holder",
                "relationship": "SUPPLIER",
                "email": "",
                "address": "",
                "tax_number": "",
                "bank_name": "Bank of Kigali",
                "bank_account_name": "Duplicate Holder",
                "bank_account_number": "0012-3456-7890",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            "This bank account already belongs",
        )
        self.assertEqual(
            Counterparty.objects.count(),
            1,
        )
