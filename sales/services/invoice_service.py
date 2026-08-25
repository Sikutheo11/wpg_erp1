from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finance.models import Receivable
from sales.models import Customer, EnterpriseInvoice


class EnterpriseInvoiceService:
    INVOICEABLE_ORDER_STATUSES = {
        "CONFIRMED", "PROCESSING", "IN_PRODUCTION",
        "READY", "DELIVERED", "COMPLETED",
    }

    @staticmethod
    def _invoice_number(order):
        return f"INV-{timezone.localdate():%Y%m%d}-{order.pk:06d}"

    @classmethod
    def resolve_customer(cls, order):
        customer = None
        if order.user_id:
            customer = Customer.objects.filter(user_id=order.user_id).first()
        if not customer and order.customer_email:
            customer = Customer.objects.filter(
                email__iexact=order.customer_email.strip()
            ).first()
        if not customer and order.customer_phone:
            customer = Customer.objects.filter(phone=order.customer_phone.strip()).first()
        if customer:
            return customer
        return Customer.objects.create(
            user=order.user,
            full_name=(order.customer_name or "").strip(),
            phone=(order.customer_phone or "").strip(),
            email=(order.customer_email or "").strip(),
            address=(order.delivery_address or "").strip(),
        )

    @classmethod
    @transaction.atomic
    def create_draft(cls, *, order, due_date=None):
        if order.status not in cls.INVOICEABLE_ORDER_STATUSES:
            raise ValidationError(
                "Only a confirmed or fulfilled order can be invoiced."
            )
        if Decimal(str(order.total_amount or 0)) <= 0:
            raise ValidationError("An invoice total must be greater than zero.")
        existing = EnterpriseInvoice.objects.filter(order=order).first()
        if existing:
            return existing
        customer = cls.resolve_customer(order)
        return EnterpriseInvoice.objects.create(
            order=order,
            customer=customer,
            invoice_number=cls._invoice_number(order),
            invoice_date=timezone.localdate(),
            due_date=due_date or timezone.localdate() + timedelta(days=30),
            subtotal=order.subtotal,
            discount=order.discount,
            tax=order.tax,
            total_amount=order.total_amount,
        )

    @classmethod
    @transaction.atomic
    def issue(cls, *, invoice, actor):
        # Lock only the invoice row. PostgreSQL rejects FOR UPDATE when the
        # query also outer-joins the nullable receivable relation.
        invoice = EnterpriseInvoice.objects.select_for_update().select_related(
            "order", "customer"
        ).get(pk=invoice.pk)
        if invoice.status == EnterpriseInvoice.VOID:
            raise ValidationError("A void invoice cannot be issued.")
        if invoice.receivable_id:
            return invoice
        receivable, created = Receivable.objects.get_or_create(
            order=invoice.order,
            defaults={
                "customer": invoice.order.user,
                "business_unit": invoice.order.business_unit,
                "transaction_date": invoice.invoice_date,
                "invoice_number": invoice.invoice_number,
                "total_amount": invoice.total_amount,
                "amount_paid": Decimal("0.00"),
                "due_date": invoice.due_date,
                "status": "unpaid",
                "notes": f"Issued from Sales order {invoice.order.order_number}.",
            },
        )
        if not created and receivable.invoice_number != invoice.invoice_number:
            raise ValidationError(
                "This order already has a different Finance receivable."
            )
        invoice.receivable = receivable
        invoice.status = EnterpriseInvoice.ISSUED
        invoice.issued_by = actor
        invoice.issued_at = timezone.now()
        invoice.save(update_fields=[
            "receivable", "status", "issued_by", "issued_at", "updated_at"
        ])
        return invoice

    @staticmethod
    def sync_payment_status(invoice):
        if invoice.status == EnterpriseInvoice.VOID or not invoice.receivable_id:
            return invoice
        if invoice.receivable.amount_paid >= invoice.total_amount:
            status = EnterpriseInvoice.PAID
        elif invoice.receivable.amount_paid > 0:
            status = EnterpriseInvoice.PARTIAL
        else:
            status = EnterpriseInvoice.ISSUED
        if invoice.status != status:
            invoice.status = status
            invoice.save(update_fields=["status", "updated_at"])
        return invoice
