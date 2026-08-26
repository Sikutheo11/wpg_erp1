from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import SalesQuotationForm
from .models import Customer, SalesQuotation
from .services.quotation_service import QuotationService


class CustomerQuotationBoundaryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="quotation-boundary-manager",
            email="quotation-boundary-manager@example.com",
            first_name="Quotation",
            last_name="Manager",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)

    def test_quotation_form_excludes_non_customer_quotation_types(self):
        values = {
            value
            for value, label in SalesQuotationForm().fields["order_type"].choices
            if value
        }
        self.assertIn("CUSTOM_FURNITURE", values)
        self.assertNotIn("ECOMMERCE", values)
        self.assertNotIn("POS", values)
        self.assertNotIn("RESTOCK", values)
        self.assertNotIn("NEW_PRODUCT", values)

    def test_service_rejects_ecommerce_quotation(self):
        customer = Customer.objects.create(
            full_name="Marketplace Customer",
            phone="0788000010",
        )
        with self.assertRaises(ValidationError):
            QuotationService.create_quotation(
                customer=customer,
                business_unit="FURNITURE",
                order_type="ECOMMERCE",
            )

    def test_legacy_ecommerce_record_is_hidden_from_quotation_engine(self):
        customer = Customer.objects.create(
            full_name="Legacy Marketplace Customer",
            phone="0788000011",
        )
        SalesQuotation.objects.create(
            customer=customer,
            quotation_no="QTN-LEGACY-ECOMMERCE",
            business_unit="FURNITURE",
            order_type="ECOMMERCE",
            valid_until=timezone.localdate() + timedelta(days=30),
        )
        response = self.client.get(reverse("sales:quotation_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "QTN-LEGACY-ECOMMERCE")
