from django.db import migrations, models


def assign_existing_departments(apps, schema_editor):
    Department = apps.get_model("Employee", "Department")
    mapping = {
        "furniture": "FURNITURE",
        "machinist": "FURNITURE",
        "construction": "CONSTRUCTION",
        "agriculture": "AGRICULTURE",
        "marketplace": "MARKETPLACE",
        "finance": "SHARED",
        "operations": "SHARED",
        "sales": "SHARED",
        "hr": "SHARED",
        "procurement": "SHARED",
        "warehouse": "SHARED",
    }
    for department in Department.objects.all().only("id", "name"):
        Department.objects.filter(pk=department.pk).update(
            business_unit=mapping.get(department.name, "SHARED")
        )


class Migration(migrations.Migration):
    dependencies = [("Employee", "0012_alter_leave_options")]

    operations = [
        migrations.AddField(
            model_name="department",
            name="business_unit",
            field=models.CharField(
                choices=[
                    ("FURNITURE", "Furniture & Manufacturing"),
                    ("CONSTRUCTION", "Construction & Built Environment"),
                    ("AGRICULTURE", "Agriculture & Poultry"),
                    ("MARKETPLACE", "Marketplace"),
                    ("SHARED", "Shared Services"),
                ],
                db_index=True,
                default="SHARED",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="department",
            name="name",
            field=models.CharField(
                choices=[
                    ("furniture", "Furniture"),
                    ("machinist", "Machinist"),
                    ("construction", "Construction"),
                    ("agriculture", "Agriculture & Poultry"),
                    ("marketplace", "Marketplace"),
                    ("finance", "Finance"),
                    ("operations", "Operations"),
                    ("sales", "Sales"),
                    ("hr", "Human Resource"),
                    ("procurement", "Procurement"),
                    ("warehouse", "Warehouse"),
                ],
                max_length=50,
                unique=True,
            ),
        ),
        migrations.RunPython(assign_existing_departments, migrations.RunPython.noop),
    ]
