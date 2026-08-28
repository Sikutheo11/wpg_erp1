from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("furniture", "0026_alter_productionjob_status_finance"),
    ]
    operations = [
        migrations.CreateModel(
            name="LabourRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role_name", models.CharField(max_length=120, unique=True)),
                ("hourly_rate", models.DecimalField(decimal_places=2, max_digits=18)),
                ("is_active", models.BooleanField(default=True)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["role_name"]},
        ),
        migrations.CreateModel(
            name="MachineRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hourly_cost", models.DecimalField(decimal_places=2, max_digits=18)),
                ("is_active", models.BooleanField(default=True)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("asset", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="furniture_machine_rate", to="inventory.asset")),
            ],
            options={"ordering": ["asset__name"]},
        ),
    ]
