from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_alter_order_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="reference_image",
            field=models.ImageField(blank=True, help_text="Customer reference photo or existing product photo.", null=True, upload_to="orders/reference_images/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="design_attachment",
            field=models.FileField(blank=True, help_text="Drawing, design, specification sheet, or supporting document.", null=True, upload_to="orders/design_attachments/%Y/%m/"),
        ),
        migrations.AddField(model_name="orderitem", name="length_cm", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="orderitem", name="width_cm", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="orderitem", name="height_cm", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="orderitem", name="material_preference", field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name="orderitem", name="colour", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="orderitem", name="finish", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="orderitem", name="customer_budget", field=models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
    ]
