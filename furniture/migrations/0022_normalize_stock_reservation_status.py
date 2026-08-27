from django.db import migrations


def normalize_reservation_statuses(apps, schema_editor):
    StockReservation = apps.get_model("furniture", "StockReservation")
    mapping = {
        "reserved": "RESERVED",
        "released": "RELEASED",
        "issued": "USED",
        "used": "USED",
        "cancelled": "CANCELLED",
    }
    for old_status, new_status in mapping.items():
        StockReservation.objects.filter(status=old_status).update(status=new_status)


def restore_legacy_statuses(apps, schema_editor):
    StockReservation = apps.get_model("furniture", "StockReservation")
    mapping = {
        "RESERVED": "reserved",
        "RELEASED": "released",
        "USED": "issued",
        "CANCELLED": "cancelled",
    }
    for current_status, legacy_status in mapping.items():
        StockReservation.objects.filter(status=current_status).update(status=legacy_status)


class Migration(migrations.Migration):
    dependencies = [
        ("furniture", "0021_quotation_communication"),
    ]

    operations = [
        migrations.RunPython(
            normalize_reservation_statuses,
            restore_legacy_statuses,
        ),
    ]
