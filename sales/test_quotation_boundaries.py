from django.core.exceptions import ValidationError
from django.test import TestCase

from .forms import SalesQuotationForm
from .models import Customer
from .services.quotation_service import QuotationService


class CustomerQuotationBoundaryTests(TestCase):
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
