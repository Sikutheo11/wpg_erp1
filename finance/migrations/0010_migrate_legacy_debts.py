from datetime import timedelta
from decimal import Decimal

from django.db import migrations


def migrate_debts(apps, schema_editor):
    DebtRecord = apps.get_model("finance", "DebtRecord")
    ObligationLine = apps.get_model("finance", "ObligationLine")
    Payable = apps.get_model("finance", "Payable")
    Receivable = apps.get_model("finance", "Receivable")
    status_map = {"DRAFT": "unpaid", "OPEN": "unpaid", "PARTIAL": "partial", "PAID": "paid", "OVERDUE": "overdue"}
    for debt in DebtRecord.objects.exclude(status="CANCELLED").select_related("counterparty", "payable", "receivable"):
        due_date = debt.due_date or (debt.transaction_date + timedelta(days=30))
        common = dict(counterparty_id=debt.counterparty_id, business_unit=debt.business_unit, transaction_date=debt.transaction_date, due_date=due_date, total_amount=debt.total_amount, amount_paid=debt.amount_paid, status=status_map.get(debt.status, "unpaid"), notes=debt.notes)
        if debt.direction == "THEY_OWE_US":
            obligation = debt.receivable
            if obligation is None:
                obligation, _created = Receivable.objects.get_or_create(invoice_number=debt.reference, defaults=common)
                debt.receivable_id = obligation.pk
                debt.save(update_fields=["receivable"])
            parent = {"receivable_id": obligation.pk, "payable_id": None}
        else:
            obligation = debt.payable
            if obligation is None:
                obligation = Payable.objects.filter(reference=debt.reference).first()
                if obligation is None:
                    obligation = Payable.objects.create(reference=debt.reference, supplier_id=getattr(debt.counterparty, "inventory_supplier_id", None), **common)
                debt.payable_id = obligation.pk
                debt.save(update_fields=["payable"])
            parent = {"payable_id": obligation.pk, "receivable_id": None}
        if not ObligationLine.objects.filter(**{key: value for key, value in parent.items() if value}).exists():
            lines = debt.lines.all()
            if lines:
                for line in lines:
                    ObligationLine.objects.create(item_type=line.item_type, product_id=line.product_id, raw_material_id=line.raw_material_id, asset_id=line.asset_id, description=line.description, quantity=line.quantity, unit=line.unit, unit_price=line.unit_price, line_total=line.line_total, **parent)
            else:
                ObligationLine.objects.create(item_type="OTHER", description=debt.notes or f"Legacy debt {debt.reference}", quantity=Decimal("1.000"), unit="item", unit_price=debt.total_amount, line_total=debt.total_amount, **parent)


class Migration(migrations.Migration):
    dependencies = [("finance", "0009_unify_payables_receivables")]
    operations = [migrations.RunPython(migrate_debts, migrations.RunPython.noop)]
