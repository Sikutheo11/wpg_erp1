from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("furniture", "0021_quotation_communication"),
        ("sales", "0007_enterprise_invoice"),
        ("orders", "0006_orderitem_furniture_specifications"),
    ]

    operations = [
        migrations.AddField(
            model_name="order", name="customer_quotation",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_order_request", to="sales.salesquotation"),
        ),
        migrations.AddField(
            model_name="order", name="production_costing",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_order_request", to="furniture.quotation"),
        ),
        migrations.AddField(
            model_name="order", name="production_authorized_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order", name="production_authorized_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="production_authorized_orders", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="order", name="status",
            field=models.CharField(choices=[("DRAFT", "Draft"), ("PENDING", "Pending"), ("AWAITING_QUOTATION", "Awaiting Quotation / Costing"), ("QUOTED", "Quotation Prepared"), ("AWAITING_CUSTOMER_APPROVAL", "Awaiting Customer Approval"), ("READY_FOR_PRODUCTION", "Ready for Production"), ("CONFIRMED", "Confirmed"), ("PROCESSING", "Processing"), ("IN_PRODUCTION", "In Production"), ("READY", "Ready"), ("DELIVERED", "Delivered"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled")], default="PENDING", max_length=30),
        ),
    ]
