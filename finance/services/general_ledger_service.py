from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.event_engine import EventEngine

from ..general_ledger_models import (
    JournalEntry,
    JournalLine,
    LedgerAccount,
)


class GeneralLedgerService:
    """
    Transaction-safe double-entry posting service.

    Journal entries are built in DRAFT, validated for equal debits and
    credits, then made immutable by changing their status to POSTED.
    Corrections are represented by reversing entries, never deletion.
    """

    @staticmethod
    def _decimal(value, field_name="amount"):
        try:
            amount = Decimal(str(value or 0)).quantize(
                Decimal("0.01")
            )
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError(
                {field_name: "Enter a valid monetary amount."}
            ) from error
        return amount

    @staticmethod
    def _user(actor):
        if actor is None:
            return None
        if hasattr(actor, "is_authenticated"):
            return actor
        return getattr(actor, "user", None)

    @staticmethod
    def _validate_account(account):
        if not isinstance(account, LedgerAccount):
            raise ValidationError("A valid ledger account is required.")
        if not account.pk:
            raise ValidationError("A saved ledger account is required.")
        if not account.is_active:
            raise ValidationError(
                f"Ledger account {account.code} is inactive."
            )

    @classmethod
    @transaction.atomic
    def create_draft(
        cls,
        *,
        description,
        entry_date=None,
        business_unit="",
        source_type="",
        source_id="",
        source_reference="",
        source_key=None,
        actor=None,
    ):
        description = (description or "").strip()
        if not description:
            raise ValidationError({"description": "Description is required."})

        source_key = (source_key or "").strip() or None
        if source_key:
            existing = (
                JournalEntry.objects
                .filter(source_key=source_key)
                .first()
            )
            if existing is not None:
                return existing, False

        entry = JournalEntry(
            entry_date=entry_date or timezone.localdate(),
            description=description,
            status=JournalEntry.DRAFT,
            business_unit=business_unit or "",
            source_type=(source_type or "").strip(),
            source_id=str(source_id or "").strip(),
            source_reference=(source_reference or "").strip(),
            source_key=source_key,
            created_by=cls._user(actor),
        )
        entry.full_clean()
        entry.save()
        return entry, True

    @classmethod
    @transaction.atomic
    def add_line(
        cls,
        *,
        entry,
        account,
        debit=Decimal("0.00"),
        credit=Decimal("0.00"),
        description="",
    ):
        if not isinstance(entry, JournalEntry) or not entry.pk:
            raise ValidationError("A saved journal entry is required.")

        entry = JournalEntry.objects.select_for_update().get(pk=entry.pk)
        if entry.status != JournalEntry.DRAFT:
            raise ValidationError(
                "Lines can only be added to a draft journal entry."
            )

        cls._validate_account(account)
        debit = cls._decimal(debit, "debit")
        credit = cls._decimal(credit, "credit")

        if debit < 0 or credit < 0:
            raise ValidationError(
                "Journal line amounts cannot be negative."
            )
        if (debit > 0) == (credit > 0):
            raise ValidationError(
                "Enter a positive debit or credit, but not both."
            )

        line = JournalLine(
            entry=entry,
            account=account,
            debit=debit,
            credit=credit,
            description=(description or "").strip(),
        )
        line.full_clean()
        line.save()
        return line

    @classmethod
    def _entry_totals(cls, entry):
        totals = (
            JournalLine.objects
            .filter(entry=entry)
            .aggregate(
                debit=Coalesce(
                    Sum("debit"),
                    Decimal("0.00"),
                ),
                credit=Coalesce(
                    Sum("credit"),
                    Decimal("0.00"),
                ),
            )
        )
        return (
            cls._decimal(totals["debit"], "debit"),
            cls._decimal(totals["credit"], "credit"),
        )

    @classmethod
    @transaction.atomic
    def post_entry(cls, *, entry, actor=None):
        if not isinstance(entry, JournalEntry) or not entry.pk:
            raise ValidationError("A saved journal entry is required.")

        entry = JournalEntry.objects.select_for_update().get(pk=entry.pk)

        if entry.status == JournalEntry.POSTED:
            return entry
        if entry.status != JournalEntry.DRAFT:
            raise ValidationError(
                "Only a draft journal entry can be posted."
            )

        debit, credit = cls._entry_totals(entry)
        if debit <= 0:
            raise ValidationError(
                "A journal entry must contain a positive amount."
            )
        if debit != credit:
            raise ValidationError(
                (
                    f"Journal entry is not balanced: "
                    f"debits {debit}, credits {credit}."
                )
            )

        entry.status = JournalEntry.POSTED
        entry.posted_by = cls._user(actor)
        entry.posted_at = timezone.now()
        entry.save(
            update_fields=[
                "status",
                "posted_by",
                "posted_at",
                "updated_at",
            ]
        )

        EventEngine.dispatch(
            event_code="FINANCE_JOURNAL_ENTRY_POSTED",
            actor=cls._user(actor),
            obj=entry,
            title="Journal Entry Posted",
            message=(
                f"{entry.entry_number} was posted for {debit} RWF."
            ),
            level="SUCCESS",
            metadata={
                "journal_entry_id": entry.pk,
                "entry_number": entry.entry_number,
                "source_type": entry.source_type,
                "source_id": entry.source_id,
                "source_reference": entry.source_reference,
                "source_key": entry.source_key,
                "business_unit": entry.business_unit,
                "debit": str(debit),
                "credit": str(credit),
            },
            notify_groups=["Finance Manager"],
            notify_owner=True,
        )
        return entry

    @classmethod
    @transaction.atomic
    def create_and_post(
        cls,
        *,
        description,
        lines,
        entry_date=None,
        business_unit="",
        source_type="",
        source_id="",
        source_reference="",
        source_key=None,
        actor=None,
    ):
        if not lines:
            raise ValidationError("At least one journal line is required.")

        entry, created = cls.create_draft(
            description=description,
            entry_date=entry_date,
            business_unit=business_unit,
            source_type=source_type,
            source_id=source_id,
            source_reference=source_reference,
            source_key=source_key,
            actor=actor,
        )

        if not created:
            if entry.status != JournalEntry.POSTED:
                raise ValidationError(
                    "The idempotency key belongs to an incomplete entry."
                )
            return entry, False

        for line_data in lines:
            if not isinstance(line_data, dict):
                raise ValidationError(
                    "Every journal line must be a dictionary."
                )
            cls.add_line(
                entry=entry,
                account=line_data.get("account"),
                debit=line_data.get("debit", Decimal("0.00")),
                credit=line_data.get("credit", Decimal("0.00")),
                description=line_data.get("description", ""),
            )

        entry = cls.post_entry(
            entry=entry,
            actor=actor,
        )
        return entry, True


    @classmethod
    @transaction.atomic
    def reverse_entry(
        cls,
        *,
        entry,
        reason,
        reversal_date=None,
        actor=None,
    ):
        if not isinstance(entry, JournalEntry) or not entry.pk:
            raise ValidationError("A saved journal entry is required.")

        entry = JournalEntry.objects.select_for_update().get(pk=entry.pk)
        reason = (reason or "").strip()

        if not reason:
            raise ValidationError({"reason": "Reversal reason is required."})
        if entry.status != JournalEntry.POSTED:
            raise ValidationError(
                "Only a posted journal entry can be reversed."
            )
        if hasattr(entry, "reversal_entry"):
            return entry.reversal_entry, False

        original_lines = list(
            entry.lines.select_related("account").order_by("pk")
        )
        if not original_lines:
            raise ValidationError(
                "The original journal entry has no lines."
            )

        reversal, created = cls.create_and_post(
            description=(
                f"Reversal of {entry.entry_number}: {reason}"
            ),
            lines=[
                {
                    "account": line.account,
                    "debit": line.credit,
                    "credit": line.debit,
                    "description": (
                        f"Reversal: {line.description}"
                        if line.description
                        else f"Reversal of line {line.pk}"
                    ),
                }
                for line in original_lines
            ],
            entry_date=reversal_date or timezone.localdate(),
            business_unit=entry.business_unit,
            source_type="JOURNAL_REVERSAL",
            source_id=str(entry.pk),
            source_reference=entry.entry_number,
            source_key=f"JOURNAL_REVERSAL:{entry.pk}",
            actor=actor,
        )

        if created:
            reversal.reversal_of = entry
            reversal.save(update_fields=["reversal_of", "updated_at"])
            entry.status = JournalEntry.REVERSED
            entry.save(update_fields=["status", "updated_at"])

        return reversal, created

    @classmethod
    def account_balance(
        cls,
        *,
        account,
        as_of=None,
    ):
        cls._validate_account(account)
        lines = JournalLine.objects.filter(
            account=account,
            entry__status=JournalEntry.POSTED,
        )
        if as_of is not None:
            lines = lines.filter(entry__entry_date__lte=as_of)

        totals = lines.aggregate(
            debit=Coalesce(Sum("debit"), Decimal("0.00")),
            credit=Coalesce(Sum("credit"), Decimal("0.00")),
        )
        debit = cls._decimal(totals["debit"])
        credit = cls._decimal(totals["credit"])

        if account.normal_balance == LedgerAccount.DEBIT:
            return debit - credit
        return credit - debit
