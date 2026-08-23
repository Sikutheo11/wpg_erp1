from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecommerce", "0010_alter_ecommercepayment_method_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="ecommercepayment",
            options={
                "ordering": ["-initiated_at", "-pk"],
                "permissions": [
                    ("confirm_ecommercepayment", "Can confirm ecommerce payments"),
                    ("refund_ecommercepayment", "Can refund ecommerce payments"),
                ],
            },
        ),
        migrations.AlterModelOptions(
            name="sellersettlement",
            options={
                "ordering": ["-created_at", "-pk"],
                "permissions": [
                    ("approve_sellersettlement", "Can approve or cancel seller settlements"),
                    ("pay_sellersettlement", "Can pay seller settlements"),
                ],
            },
        ),
    ]
