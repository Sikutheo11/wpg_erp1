from django.db import migrations, models


def deduplicate_references(apps, schema_editor):
    Payable = apps.get_model("finance", "Payable")
    seen = set()
    for payable in Payable.objects.order_by("pk"):
        reference = (payable.reference or f"PAY-{payable.pk}").strip()
        candidate = reference
        if candidate in seen:
            candidate = f"{reference[:88]}-{payable.pk}"
        while candidate in seen:
            candidate = f"{reference[:84]}-{payable.pk}-{len(seen)}"
        if candidate != payable.reference:
            payable.reference = candidate
            payable.save(update_fields=["reference"])
        seen.add(candidate)


class Migration(migrations.Migration):
    dependencies = [("finance", "0010_migrate_legacy_debts")]
    operations = [
        migrations.RunPython(deduplicate_references, migrations.RunPython.noop),
        migrations.AlterField(model_name="payable", name="reference", field=models.CharField(max_length=100, unique=True)),
        migrations.AlterField(model_name="payable", name="status", field=models.CharField(choices=(("unpaid", "Unpaid"), ("partial", "Partial"), ("paid", "Paid"), ("overdue", "Overdue")), default="unpaid", max_length=20)),
    ]
