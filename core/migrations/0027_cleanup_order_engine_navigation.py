from django.db import migrations


LEGACY_CODES = (
    "SALES_LIST",
    "SALES_PAYMENTS",
)


def cleanup_order_engine_navigation(apps, schema_editor):
    Feature = apps.get_model("core", "Feature")

    # Keep legacy data/models available, but remove obsolete navigation
    # entries now superseded by the enterprise Order/Finance workflows.
    Feature.objects.filter(
        code__in=LEGACY_CODES,
    ).update(is_active=False)

    # Remove unresolved placeholder navigation only when it has no route.
    Feature.objects.filter(
        name__iexact="Order Detail",
        url_name="",
    ).update(is_active=False)


def reverse_cleanup(apps, schema_editor):
    Feature = apps.get_model("core", "Feature")

    Feature.objects.filter(
        code__in=LEGACY_CODES,
    ).update(is_active=True)

    Feature.objects.filter(
        name__iexact="Order Detail",
        url_name="",
    ).update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_jobinvestment_jobinvestoragreement_and_more"),
    ]

    operations = [
        migrations.RunPython(
            cleanup_order_engine_navigation,
            reverse_cleanup,
        ),
    ]
