import re

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone

from sales.models import EnterpriseInvoice, InvoiceDelivery
from sales.pdf import render_enterprise_invoice_pdf


class InvoiceDeliveryService:
    @staticmethod
    def public_url(invoice, request=None):
        path = reverse("sales:invoice_public_pdf", kwargs={"token": invoice.public_token})
        if request:
            return request.build_absolute_uri(path)
        base = getattr(settings, "PUBLIC_BASE_URL", "").rstrip("/")
        if not base:
            raise ValidationError("PUBLIC_BASE_URL is not configured.")
        return base + path

    @classmethod
    def send_email(cls, *, invoice, actor, request=None):
        destination = (invoice.customer.email or invoice.order.customer_email or "").strip()
        if not destination:
            raise ValidationError("This customer has no email address.")
        delivery = InvoiceDelivery.objects.create(
            invoice=invoice, channel=InvoiceDelivery.EMAIL,
            destination=destination, sent_by=actor,
        )
        try:
            pdf = render_enterprise_invoice_pdf(invoice)
            message = EmailMessage(
                subject=f"WPG Invoice {invoice.invoice_number}",
                body=(
                    f"Dear {invoice.customer.display_name},\n\n"
                    f"Please find invoice {invoice.invoice_number} attached. "
                    f"Amount due: {invoice.balance:,.2f} RWF.\n\nWisdom Palace Group"
                ),
                to=[destination],
            )
            message.attach(f"{invoice.invoice_number}.pdf", pdf, "application/pdf")
            message.send(fail_silently=False)
            delivery.status = InvoiceDelivery.SENT
            delivery.sent_at = timezone.now()
        except Exception as error:
            delivery.status = InvoiceDelivery.FAILED
            delivery.error_message = str(error)[:2000]
            delivery.save(update_fields=["status", "error_message"])
            raise
        delivery.save(update_fields=["status", "sent_at"])
        return delivery

    @classmethod
    def send_whatsapp(cls, *, invoice, actor, request=None):
        phone = re.sub(r"\D", "", invoice.customer.phone or invoice.order.customer_phone or "")
        if not phone:
            raise ValidationError("This customer has no WhatsApp phone number.")
        phone_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
        token = getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
        template = getattr(settings, "WHATSAPP_INVOICE_TEMPLATE", "wpg_invoice")
        language = getattr(settings, "WHATSAPP_TEMPLATE_LANGUAGE", "en")
        if not phone_id or not token:
            raise ValidationError("WhatsApp Business API is not configured.")
        delivery = InvoiceDelivery.objects.create(
            invoice=invoice, channel=InvoiceDelivery.WHATSAPP,
            destination=phone, sent_by=actor,
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": language},
                "components": [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": invoice.customer.display_name},
                        {"type": "text", "text": invoice.invoice_number},
                        {"type": "text", "text": f"{invoice.balance:.2f} RWF"},
                        {"type": "text", "text": cls.public_url(invoice, request)},
                    ],
                }],
            },
        }
        try:
            api_version = getattr(settings, "WHATSAPP_GRAPH_API_VERSION", "v23.0")
            response = requests.post(
                f"https://graph.facebook.com/{api_version}/{phone_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json=payload, timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            delivery.provider_message_id = ((data.get("messages") or [{}])[0].get("id", ""))
            delivery.status = InvoiceDelivery.SENT
            delivery.sent_at = timezone.now()
        except Exception as error:
            delivery.status = InvoiceDelivery.FAILED
            delivery.error_message = str(error)[:2000]
            delivery.save(update_fields=["status", "error_message"])
            raise
        delivery.save(update_fields=["status", "provider_message_id", "sent_at"])
        return delivery
