from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0005_alter_customer_options_alter_salesquotation_options_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="salesquotation",
            options={
                "ordering": ["-created_at"],
                "permissions": [
                    (
                        "approve_salesquotation",
                        "Can approve or reject sales quotations",
                    ),
                    (
                        "convert_salesquotation",
                        "Can convert sales quotations to orders",
                    ),
                ],
            },
        ),
    ]
