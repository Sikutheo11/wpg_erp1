import core.file_validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_order_production_authorization"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="reference_image",
            field=models.ImageField(
                blank=True,
                help_text="Customer reference photo or existing product photo.",
                null=True,
                upload_to="orders/reference_images/%Y/%m/",
                validators=[
                    core.file_validators.SecureFileValidator(
                        allowed_extensions=("jpg", "jpeg", "png", "webp"),
                        max_size_mb=5,
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="design_attachment",
            field=models.FileField(
                blank=True,
                help_text=(
                    "Drawing, design, specification sheet, or supporting document."
                ),
                null=True,
                upload_to="orders/design_attachments/%Y/%m/",
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
