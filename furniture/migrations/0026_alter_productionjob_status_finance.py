from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("furniture", "0025_productionoutput_inventory_movement_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productionjob",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Draft / Design"),
                    ("DESIGN", "Design"),
                    ("COSTING", "Costing / BOM"),
                    ("QUOTATION", "Quotation"),
                    ("APPROVED", "Approved"),
                    ("ORDER_CONFIRMED", "Order Confirmed"),
                    ("PRODUCTION_PLAN", "Production Plan"),
                    ("FUNDING_CHECK", "Funding Check"),
                    ("MATERIAL_RESERVED", "Material Reserved"),
                    ("IN_PRODUCTION", "In Production"),
                    ("QUALITY_CHECK", "Quality Check"),
                    ("READY_FOR_FINISHED_GOODS", "Ready for Finished Goods"),
                    ("FINISHED_GOODS", "Finished Goods"),
                    ("DELIVERED", "Delivered"),
                    ("FINANCE", "Finance / Profit Review"),
                    ("CLOSED", "Closed"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="QUOTATION",
                max_length=30,
            ),
        ),
    ]
