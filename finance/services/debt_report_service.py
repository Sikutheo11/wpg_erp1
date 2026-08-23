from decimal import Decimal

from django.db.models import Q

from ..models import Payable, Receivable


class DebtReportService:
    @staticmethod
    def build(params):
        search = params.get("q", "").strip()
        direction = params.get("direction", "").strip().upper()
        status = params.get("status", "").strip().lower()
        unit = params.get("business_unit", "").strip().upper()
        payables = Payable.objects.select_related("counterparty", "supplier")
        receivables = Receivable.objects.select_related("counterparty", "customer", "order")
        if search:
            payables = payables.filter(Q(reference__icontains=search) | Q(counterparty__name__icontains=search) | Q(counterparty__phone__icontains=search))
            receivables = receivables.filter(Q(invoice_number__icontains=search) | Q(counterparty__name__icontains=search) | Q(counterparty__phone__icontains=search))
        if status in {"unpaid", "partial", "paid", "overdue"}:
            payables, receivables = payables.filter(status=status), receivables.filter(status=status)
        if unit:
            payables, receivables = payables.filter(business_unit=unit), receivables.filter(business_unit=unit)
        rows = []
        if direction != "RECEIVABLE":
            rows += [DebtReportService._row(item, "PAYABLE") for item in payables]
        if direction != "PAYABLE":
            rows += [DebtReportService._row(item, "RECEIVABLE") for item in receivables]
        rows.sort(key=lambda row: (row["date"], row["pk"]), reverse=True)
        payable_balance = sum((r["balance"] for r in rows if r["direction"] == "PAYABLE"), Decimal("0"))
        receivable_balance = sum((r["balance"] for r in rows if r["direction"] == "RECEIVABLE"), Decimal("0"))
        return {"rows": rows, "payable_balance": payable_balance, "receivable_balance": receivable_balance, "net": receivable_balance - payable_balance, "total": sum((r["total"] for r in rows), Decimal("0")), "paid": sum((r["paid"] for r in rows), Decimal("0"))}

    @staticmethod
    def _row(item, direction):
        party = item.counterparty
        fallback = item.supplier if direction == "PAYABLE" else item.customer
        return {"pk": item.pk, "direction": direction, "reference": item.reference if direction == "PAYABLE" else item.invoice_number, "party": party.name if party else str(fallback or "—"), "phone": party.phone if party else "", "date": item.transaction_date, "due_date": item.due_date, "business_unit": item.business_unit, "total": item.total_amount, "paid": item.amount_paid, "balance": item.balance, "status": item.status, "url_name": "finance:payable_detail" if direction == "PAYABLE" else "finance:receivable_detail"}
