from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("furniture", "0020_alter_qualityinspection_quotation_and_more")]
    operations = [
        migrations.AddField(
            model_name="quotation",
            name="notes",
            field=models.TextField(
                blank=True,
                help_text="Costing assumptions, material notes, and communication for reviewers.",
            ),
        ),
        migrations.AddField(model_name="quotation", name="approval_note", field=models.TextField(blank=True)),
        migrations.AddField(model_name="quotation", name="approved_at", field=models.DateTimeField(blank=True, null=True)),
    ]
