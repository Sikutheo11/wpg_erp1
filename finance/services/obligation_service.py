from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from ..models import ObligationLine, Payable, Receivable


class ObligationService:
    """Creates payable/receivable headers and their itemized lines atomically."""

    @staticmethod
    def _status(total, paid, due_date, choices):
        values = {value for value, _label in choices}
        if paid >= total:
            return "paid"
        if paid > 0:
            return "partial"
        if due_date < timezone.localdate() and "overdue" in values:
            return "overdue"
        return "unpaid"

    @classmethod
    def recalculate(cls, obligation):
        total = obligation.lines.aggregate(total=Sum("line_total"))["total"] or Decimal("0.00")
        obligation.total_amount = total
        obligation.status = cls._status(
            total, obligation.amount_paid, obligation.due_date, obligation.STATUS
        )
        obligation.save(update_fields=["total_amount", "status"])
        return obligation

    @classmethod
    @transaction.atomic
    def create(cls, *, form, formset, kind):
        if kind not in {"payable", "receivable"}:
            raise ValueError("Unknown obligation kind.")
        obligation = form.save(commit=False)
        obligation.total_amount = Decimal("0.00")
        obligation.amount_paid = Decimal("0.00")
        obligation.status = "unpaid"
        counterparty = obligation.counterparty
        if kind == "payable":
            counterparty.is_supplier = True
            if hasattr(counterparty, "inventory_supplier"):
                obligation.supplier = counterparty.inventory_supplier
        else:
            counterparty.is_customer = True
        counterparty.save(update_fields=["is_customer", "is_supplier"])
        obligation.save()
        formset.instance = obligation
        lines = formset.save(commit=False)
        if not lines:
            raise ValidationError("Add at least one item.")
        for line in lines:
            if kind == "payable":
                line.payable = obligation
                line.receivable = None
            else:
                line.receivable = obligation
                line.payable = None
            line.full_clean()
            line.save()
        return cls.recalculate(obligation)
