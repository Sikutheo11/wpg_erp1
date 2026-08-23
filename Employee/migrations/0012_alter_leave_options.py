from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Employee", "0011_remove_leave_approved_leave_status_leave_updated_at"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="leave",
            options={
                "permissions": [
                    (
                        "approve_leave",
                        "Can approve or reject leave requests",
                    ),
                ],
            },
        ),
    ]
