from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("furniture", "0019_alter_productionoutput_options")]

    operations = [
        migrations.AlterModelOptions(
            name="quotation",
            options={
                "permissions": [("approve_quotation", "Can approve furniture quotations")],
            },
        ),
        migrations.AlterModelOptions(
            name="qualityinspection",
            options={
                "ordering": ["-inspected_at"],
                "permissions": [("approve_qualityinspection", "Can approve furniture quality inspections")],
            },
        ),
        migrations.AlterModelOptions(
            name="reworkorder",
            options={
                "ordering": ["-created_at"],
                "permissions": [("verify_reworkorder", "Can verify furniture rework orders")],
            },
        ),
    ]
