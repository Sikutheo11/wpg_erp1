from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_alter_order_order_type"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="order",
            options={
                "permissions": [
                    (
                        "approve_order",
                        "Can confirm or cancel enterprise orders",
                    ),
                    (
                        "fulfil_order",
                        "Can process and deliver enterprise orders",
                    ),
                ],
            },
        ),
    ]
