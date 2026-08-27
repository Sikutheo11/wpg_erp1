from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0015_secure_document_uploads"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="finance_tx_amount_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="income",
            constraint=models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="finance_income_amount_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="incomedeclaration",
            constraint=models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="finance_income_decl_amount_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="expense",
            constraint=models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="finance_expense_amount_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="expenserequest",
            constraint=models.CheckConstraint(
                condition=models.Q(amount_requested__gt=0),
                name="finance_exp_req_requested_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="expenserequest",
            constraint=models.CheckConstraint(
                condition=models.Q(amount_paid__gte=0),
                name="finance_exp_req_paid_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="receivable",
            constraint=models.CheckConstraint(
                condition=models.Q(total_amount__gt=0),
                name="finance_recv_total_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="receivable",
            constraint=models.CheckConstraint(
                condition=models.Q(amount_paid__gte=0),
                name="finance_recv_paid_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="receivable",
            constraint=models.CheckConstraint(
                condition=models.Q(amount_paid__lte=models.F("total_amount")),
                name="finance_recv_paid_lte_total",
            ),
        ),
        migrations.AddConstraint(
            model_name="payable",
            constraint=models.CheckConstraint(
                condition=models.Q(total_amount__gt=0),
                name="finance_pay_total_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="payable",
            constraint=models.CheckConstraint(
                condition=models.Q(amount_paid__gte=0),
                name="finance_pay_paid_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="payable",
            constraint=models.CheckConstraint(
                condition=models.Q(amount_paid__lte=models.F("total_amount")),
                name="finance_pay_paid_lte_total",
            ),
        ),
    ]
