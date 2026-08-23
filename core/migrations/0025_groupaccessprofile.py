import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0024_configure_inventory_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="GroupAccessProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "priority",
                    models.PositiveIntegerField(
                        default=100,
                        help_text=(
                            "Lower values win when a user belongs "
                            "to several groups."
                        ),
                    ),
                ),
                (
                    "group",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_profile",
                        to="auth.group",
                    ),
                ),
                (
                    "landing_feature",
                    models.ForeignKey(
                        help_text=(
                            "The first page opened after a member "
                            "of this group logs in."
                        ),
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="landing_groups",
                        to="core.feature",
                    ),
                ),
            ],
            options={
                "ordering": ["priority", "group__name"],
            },
        ),
    ]
