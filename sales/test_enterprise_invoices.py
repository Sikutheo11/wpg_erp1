from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from finance.models import Receivable
from orders.models import Order
from sales.models import Customer, EnterpriseInvoice, InvoiceDelivery
from sales.services.invoice_delivery_service import InvoiceDeliveryService
from sales.services.invoice_service import EnterpriseInvoiceService


class EnterpriseInvoiceWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="invoice.manager@test.local",
            email="invoice.manager@test.local",
            first_name="Invoice",
            last_name="Manager",
            password="test-pass",
        )
        self.customer = Customer.objects.create(
            full_name="Test Customer", phone="+250788000001",
            email="customer@test.local",
        )
        self.order = Order.objects.create(
            user=None, business_unit="FURNITURE", order_type="CUSTOM_ORDER",
            status="CONFIRMED", customer_name=self.customer.full_name,
            customer_phone=self.customer.phone, customer_email=self.customer.email,
            subtotal=Decimal("100000.00"), discount=Decimal("5000.00"),
            tax=Decimal("0.00"), total_amount=Decimal("95000.00"),
        )

    def create_invoice(self):
        return EnterpriseInvoiceService.create_draft(
            order=self.order, due_date=timezone.localdate() + timedelta(days=30)
        )

    def test_draft_uses_existing_customer_and_is_unique_per_order(self):
        first = self.create_invoice()
        second = self.create_invoice()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.customer, self.customer)
        self.assertEqual(EnterpriseInvoice.objects.filter(order=self.order).count(), 1)

    def test_issue_creates_exactly_one_finance_receivable(self):
        invoice = self.create_invoice()
        EnterpriseInvoiceService.issue(invoice=invoice, actor=self.user)
        EnterpriseInvoiceService.issue(invoice=invoice, actor=self.user)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, EnterpriseInvoice.ISSUED)
        self.assertEqual(Receivable.objects.filter(order=self.order).count(), 1)
        self.assertEqual(invoice.receivable.total_amount, Decimal("95000.00"))

    def test_unconfirmed_order_cannot_be_invoiced(self):
        self.order.status = "PENDING"
        self.order.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            self.create_invoice()

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_has_pdf_attachment_and_delivery_log(self):
        invoice = EnterpriseInvoiceService.issue(invoice=self.create_invoice(), actor=self.user)
        delivery = InvoiceDeliveryService.send_email(invoice=invoice, actor=self.user)
        self.assertEqual(delivery.status, InvoiceDelivery.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].attachments[0][2], "application/pdf")

    @override_settings(
        WHATSAPP_PHONE_NUMBER_ID="123", WHATSAPP_ACCESS_TOKEN="secret",
        PUBLIC_BASE_URL="https://example.test",
    )
    @patch("sales.services.invoice_delivery_service.requests.post")
    def test_whatsapp_uses_template_and_records_provider_id(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"messages": [{"id": "wamid.123"}]}
        post.return_value = response
        invoice = EnterpriseInvoiceService.issue(invoice=self.create_invoice(), actor=self.user)
        delivery = InvoiceDeliveryService.send_whatsapp(invoice=invoice, actor=self.user)
        self.assertEqual(delivery.status, InvoiceDelivery.SENT)
        self.assertEqual(delivery.provider_message_id, "wamid.123")
        call = post.call_args
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertNotIn("secret", str(call.kwargs["json"]))
        self.assertNotIn("secret", delivery.error_message)

    @override_settings(WHATSAPP_PHONE_NUMBER_ID="", WHATSAPP_ACCESS_TOKEN="")
    def test_missing_whatsapp_configuration_is_safe(self):
        invoice = EnterpriseInvoiceService.issue(invoice=self.create_invoice(), actor=self.user)
        with self.assertRaises(ValidationError):
            InvoiceDeliveryService.send_whatsapp(invoice=invoice, actor=self.user)
