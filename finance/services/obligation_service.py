from decimal import Decimal
from datetime import timedelta
import uuid

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
        today = timezone.localdate()
        obligation.due_date = obligation.transaction_date + timedelta(days=30)
        obligation.notes = ""
        token = uuid.uuid4().hex[:8].upper()
        if kind == "payable":
            obligation.reference = f"PAY-{today:%Y%m%d}-{token}"
        else:
            obligation.invoice_number = f"REC-{today:%Y%m%d}-{token}"
        lines = formset.save(commit=False)
        if not lines:
            raise ValidationError("Add at least one item.")
        initial_total = sum(
            (
                Decimal(str(line.quantity))
                * Decimal(str(line.unit_price))
            ).quantize(Decimal("0.01"))
            for line in lines
        )
        if initial_total <= 0:
            raise ValidationError("The obligation total must be greater than zero.")
        # PostgreSQL checks the positive-total constraint when the parent is
        # inserted. Calculate the formset total before that insert instead of
        # temporarily saving an invalid zero-value header.
        obligation.total_amount = initial_total
        obligation.amount_paid = Decimal("0.00")
        obligation.status = "unpaid"
        counterparty = obligation.counterparty
        if counterparty is None:
            raise ValidationError("Select the person or company linked to this obligation.")
        if kind == "payable":
            counterparty.is_supplier = True
            if hasattr(counterparty, "inventory_supplier"):
                obligation.supplier = counterparty.inventory_supplier
        else:
            counterparty.is_customer = True
        counterparty.save(update_fields=["is_customer", "is_supplier"])
        obligation.save()
        formset.instance = obligation
        for line in lines:
            if kind == "payable":
                line.payable = obligation
                line.receivable = None
            else:
                line.receivable = obligation
                line.payable = None
            if line.catalog_item_id:
                line.item_type = ObligationLine.OTHER
                line.description = line.catalog_item.name
                line.unit = line.catalog_item.default_unit
            line.full_clean()
            line.save()
        return cls.recalculate(obligation)
