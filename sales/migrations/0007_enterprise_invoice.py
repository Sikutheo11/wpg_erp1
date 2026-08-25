import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0013_expense_request_workflow"),
        ("orders", "0005_alter_order_options"),
        ("sales", "0006_alter_salesquotation_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EnterpriseInvoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("invoice_number", models.CharField(max_length=50, unique=True)),
                ("invoice_date", models.DateField(default=django.utils.timezone.localdate)),
                ("due_date", models.DateField()),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=15)),
                ("discount", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("tax", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=15)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("ISSUED", "Issued"), ("PARTIAL", "Partially paid"), ("PAID", "Paid"), ("VOID", "Void")], default="DRAFT", max_length=20)),
                ("public_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("issued_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enterprise_invoices", to="sales.customer")),
                ("issued_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="issued_sales_invoices", to=settings.AUTH_USER_MODEL)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="sales_invoice", to="orders.order")),
                ("receivable", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sales_invoice", to="finance.receivable")),
            ],
            options={
                "ordering": ["-invoice_date", "-pk"],
                "permissions": [("issue_enterpriseinvoice", "Can issue enterprise invoices"), ("send_enterpriseinvoice", "Can send enterprise invoices"), ("void_enterpriseinvoice", "Can void enterprise invoices")],
            },
        ),
        migrations.CreateModel(
            name="InvoiceDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel", models.CharField(choices=[("EMAIL", "Email"), ("WHATSAPP", "WhatsApp")], max_length=20)),
                ("destination", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("SENT", "Sent"), ("FAILED", "Failed")], default="PENDING", max_length=20)),
                ("provider_message_id", models.CharField(blank=True, max_length=255)),
                ("error_message", models.TextField(blank=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deliveries", to="sales.enterpriseinvoice")),
                ("sent_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sent_sales_invoices", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
