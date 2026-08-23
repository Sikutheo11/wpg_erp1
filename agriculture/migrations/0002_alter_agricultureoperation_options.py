from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("agriculture", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="agricultureoperation",
            options={
                "ordering": ["-created_at", "-pk"],
                "permissions": [
                    (
                        "approve_agricultureoperation",
                        "Can approve or return agriculture operations",
                    ),
                    (
                        "complete_agricultureoperation",
                        "Can complete agriculture operations",
                    ),
                ],
            },
        ),
    ]
