import core.file_validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0014_atomic_finance_posting"),
    ]

    operations = [
        migrations.AlterField(
            model_name="incomedeclaration",
            name="proof_document",
            field=models.FileField(
                blank=True,
                upload_to="finance/income_declarations/%Y/%m/",
                validators=[
                    core.file_validators.SecureFileValidator(
                        allowed_extensions=(
                            "pdf", "jpg", "jpeg", "png", "webp",
                        ),
                        max_size_mb=8,
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="expenserequest",
            name="supporting_document",
            field=models.FileField(
                blank=True,
                upload_to="finance/expense_requests/%Y/%m/",
                validators=[
                    core.file_validators.SecureFileValidator(
                        allowed_extensions=(
                            "pdf", "jpg", "jpeg", "png", "webp",
                            "doc", "docx", "xls", "xlsx",
                        ),
                        max_size_mb=12,
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="expenserequest",
            name="accountability_document",
            field=models.FileField(
                blank=True,
                upload_to="finance/accountability/%Y/%m/",
                validators=[
                    core.file_validators.SecureFileValidator(
                        allowed_extensions=(
                            "pdf", "jpg", "jpeg", "png", "webp",
                            "doc", "docx", "xls", "xlsx",
                        ),
                        max_size_mb=12,
                    )
                ],
            ),
        ),
    ]
