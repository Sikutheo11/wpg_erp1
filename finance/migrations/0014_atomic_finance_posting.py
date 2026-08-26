from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0013_expense_request_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="posting_key",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text=(
                    "Stable source identifier used to prevent duplicate "
                    "account postings."
                ),
                max_length=160,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="income",
            name="ledger_transaction",
            field=models.OneToOneField(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="income_record",
                to="finance.transaction",
            ),
        ),
        migrations.AddField(
            model_name="expense",
            name="ledger_transaction",
            field=models.OneToOneField(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="expense_record",
                to="finance.transaction",
            ),
        ),
    ]
