from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0008_secure_order_uploads"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="order",
            constraint=models.CheckConstraint(
                condition=models.Q(subtotal__gte=0),
                name="orders_order_subtotal_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.CheckConstraint(
                condition=models.Q(discount__gte=0),
                name="orders_order_discount_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.CheckConstraint(
                condition=models.Q(tax__gte=0),
                name="orders_order_tax_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name="orders_order_total_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="orderitem",
            constraint=models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="orders_item_quantity_gt_zero",
            ),
        ),
        migrations.AddConstraint(
            model_name="orderitem",
            constraint=models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="orders_item_price_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="orderitem",
            constraint=models.CheckConstraint(
                condition=models.Q(length_cm__isnull=True) | models.Q(length_cm__gt=0),
                name="orders_item_length_positive_or_null",
            ),
        ),
        migrations.AddConstraint(
            model_name="orderitem",
            constraint=models.CheckConstraint(
                condition=models.Q(width_cm__isnull=True) | models.Q(width_cm__gt=0),
                name="orders_item_width_positive_or_null",
            ),
        ),
        migrations.AddConstraint(
            model_name="orderitem",
            constraint=models.CheckConstraint(
                condition=models.Q(height_cm__isnull=True) | models.Q(height_cm__gt=0),
                name="orders_item_height_positive_or_null",
            ),
        ),
        migrations.AddConstraint(
            model_name="orderitem",
            constraint=models.CheckConstraint(
                condition=models.Q(customer_budget__isnull=True) | models.Q(customer_budget__gte=0),
                name="orders_item_budget_nonnegative_or_null",
            ),
        ),
    ]
