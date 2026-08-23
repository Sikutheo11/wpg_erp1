from django.db import migrations, models
from decimal import Decimal
import django.db.models.deletion
import django.utils.timezone


BUSINESS_UNITS = (
    ("GENERAL", "WPG General"),
    ("FURNITURE", "Furniture & Manufacturing"),
    ("CONSTRUCTION", "Construction"),
    ("AGRICULTURE", "Agriculture / Poultry"),
    ("MARKETPLACE", "Marketplace"),
)


class Migration(migrations.Migration):
    dependencies = [
        ("Employee", "0012_alter_leave_options"),
        ("inventory", "0009_alter_category_options_alter_product_options_and_more"),
        ("finance", "0008_support_debt_raw_materials_and_assets"),
    ]

    operations = [
        migrations.AddField(model_name="receivable", name="counterparty", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivables", to="finance.counterparty")),
        migrations.AddField(model_name="receivable", name="business_unit", field=models.CharField(choices=BUSINESS_UNITS, db_index=True, default="GENERAL", max_length=30)),
        migrations.AddField(model_name="receivable", name="transaction_date", field=models.DateField(default=django.utils.timezone.localdate)),
        migrations.AddField(model_name="receivable", name="notes", field=models.TextField(blank=True)),
        migrations.AddField(model_name="payable", name="counterparty", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payables", to="finance.counterparty")),
        migrations.AddField(model_name="payable", name="business_unit", field=models.CharField(choices=BUSINESS_UNITS, db_index=True, default="GENERAL", max_length=30)),
        migrations.AddField(model_name="payable", name="transaction_date", field=models.DateField(default=django.utils.timezone.localdate)),
        migrations.AddField(model_name="payable", name="notes", field=models.TextField(blank=True)),
        migrations.AlterField(model_name="payable", name="supplier", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="inventory.supplier")),
        migrations.CreateModel(
            name="ObligationLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("item_type", models.CharField(choices=(("PRODUCT", "Product"), ("RAW_MATERIAL", "Raw material"), ("ASSET", "Asset"), ("WORKER", "Worker"), ("TAX", "Tax"), ("CASUAL_WORK", "Casual work"), ("TRANSPORT", "Transport"), ("RENT", "Rent"), ("UTILITY", "Utility"), ("SERVICE", "Service"), ("OTHER", "Other")), default="OTHER", max_length=20)),
                ("description", models.CharField(blank=True, max_length=300)),
                ("quantity", models.DecimalField(decimal_places=3, default=Decimal("1.000"), max_digits=14)),
                ("unit", models.CharField(default="piece", max_length=30)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=15)),
                ("line_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), editable=False, max_digits=15)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("asset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="inventory.asset")),
                ("payable", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="finance.payable")),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="inventory.product")),
                ("raw_material", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="inventory.rawmaterial")),
                ("receivable", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="finance.receivable")),
                ("worker", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="Employee.employee")),
            ],
            options={"ordering": ["pk"]},
        ),
        migrations.AddConstraint(model_name="obligationline", constraint=models.CheckConstraint(condition=(models.Q(payable__isnull=True, receivable__isnull=False) | models.Q(payable__isnull=False, receivable__isnull=True)), name="fin_obligation_line_one_parent")),
        migrations.AddConstraint(model_name="obligationline", constraint=models.CheckConstraint(condition=models.Q(("quantity__gt", 0)), name="fin_obligation_line_qty_gt_zero")),
        migrations.AddConstraint(model_name="obligationline", constraint=models.CheckConstraint(condition=models.Q(("unit_price__gte", 0)), name="fin_obligation_line_price_nonnegative")),
    ]
