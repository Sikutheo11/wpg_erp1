from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine

from ..general_ledger_models import (
    CustomerAdvance,
    JournalEntry,
    LedgerAccount,
)
from .general_ledger_service import GeneralLedgerService


class CustomerAdvanceService:
    """
    Records money received before revenue has been earned.

    Receipt:
        Dr Cash / Bank / Mobile Money
        Cr Customer Advances

    Application after fulfilment/delivery:
        Dr Customer Advances
        Cr Business Unit Revenue

    Refund:
        Dr Customer Advances
        Cr Cash / Bank / Mobile Money

    Every posting uses a stable source_key so retries cannot post the same
    business event twice.
    """

    CUSTOMER_ADVANCES_ACCOUNT = "2100"

    PAYMENT_ACCOUNT_CODES = {
        "cash": "1100",
        "bank": "1110",
        "mobile": "1120",
        "mobile_money": "1120",
    }

    REVENUE_ACCOUNT_CODES = {
        "FURNITURE": "4100",
        "AGRICULTURE": "4200",
        "CONSTRUCTION": "4300",
        "MARKETPLACE": "4400",
    }

    @staticmethod
    def _user(actor):
        if actor is None:
            return None
        if hasattr(actor, "is_authenticated"):
            return actor
        return getattr(actor, "user", None)

    @staticmethod
    def _amount(value, field_name="amount"):
        try:
            amount = Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError(
                {field_name: "Enter a valid monetary amount."}
            ) from error

        if amount <= 0:
            raise ValidationError(
                {field_name: "Amount must be greater than zero."}
            )
        return amount

    @staticmethod
    def _clean_required(value, field_name):
        value = str(value or "").strip()
        if not value:
            raise ValidationError(
                {field_name: f"{field_name.replace('_', ' ').title()} is required."}
            )
        return value

    @classmethod
    def _account(cls, code):
        code = cls._clean_required(code, "account_code")
        try:
            return LedgerAccount.objects.get(
                code=code,
                is_active=True,
            )
        except LedgerAccount.DoesNotExist as error:
            raise ValidationError(
                f"Active ledger account {code} was not found. "
                "Run seed_chart_of_accounts first."
            ) from error

    @classmethod
    def _payment_account(cls, payment_method=None, account_code=None):
        if account_code:
            account = cls._account(account_code)
        else:
            method = str(payment_method or "").strip().lower()
            code = cls.PAYMENT_ACCOUNT_CODES.get(method)
            if code is None:
                raise ValidationError(
                    {
                        "payment_method": (
                            "Use cash, bank, mobile, or mobile_money."
                        )
                    }
                )
            account = cls._account(code)

        if account.account_type != LedgerAccount.ASSET:
            raise ValidationError(
                f"Payment account {account.code} must be an asset account."
            )
        return account

    @classmethod
    def _revenue_account(cls, business_unit):
        business_unit = cls._clean_required(
            business_unit,
            "business_unit",
        ).upper()
        code = cls.REVENUE_ACCOUNT_CODES.get(business_unit)
        if code is None:
            raise ValidationError(
                {
                    "business_unit": (
                        f"No revenue account is configured for {business_unit}."
                    )
                }
            )

        account = cls._account(code)
        if account.account_type != LedgerAccount.REVENUE:
            raise ValidationError(
                f"Account {account.code} must be a revenue account."
            )
        return business_unit, account

    @staticmethod
    def _set_status(advance):
        available = advance.available_amount

        if available == advance.amount:
            advance.status = CustomerAdvance.AVAILABLE
        elif available > 0 and advance.applied_amount > 0:
            advance.status = CustomerAdvance.PARTIALLY_APPLIED
        elif available > 0 and advance.refunded_amount > 0:
            advance.status = CustomerAdvance.PARTIALLY_REFUNDED
        elif advance.applied_amount == advance.amount:
            advance.status = CustomerAdvance.APPLIED
        elif advance.refunded_amount == advance.amount:
            advance.status = CustomerAdvance.REFUNDED
        elif available == 0 and advance.applied_amount > 0:
            # An advance may be partly recognized as revenue and partly
            # refunded. Nothing remains available in either case.
            advance.status = CustomerAdvance.APPLIED
        else:
            advance.status = CustomerAdvance.AVAILABLE

    @classmethod
    def _receipt_cash_account(cls, advance):
        if advance.receipt_entry_id is None:
            raise ValidationError(
                "The advance has no receipt journal entry."
            )

        line = (
            advance.receipt_entry.lines
            .select_related("account")
            .filter(
                debit__gt=0,
                account__account_type=LedgerAccount.ASSET,
            )
            .order_by("pk")
            .first()
        )
        if line is None:
            raise ValidationError(
                "The receipt journal has no debited asset account."
            )
        return line.account

    @classmethod
    def _dispatch(cls, *, event_code, advance, actor, title, message, metadata):
        EventEngine.dispatch(
            event_code=event_code,
            actor=cls._user(actor),
            obj=advance,
            title=title,
            message=message,
            level="SUCCESS",
            metadata={
                "customer_advance_id": advance.pk,
                "advance_reference": advance.reference,
                "source_type": advance.source_type,
                "source_id": advance.source_id,
                "amount": str(advance.amount),
                "applied_amount": str(advance.applied_amount),
                "refunded_amount": str(advance.refunded_amount),
                "available_amount": str(advance.available_amount),
                **metadata,
            },
            notify_groups=["Finance Manager"],
            notify_owner=True,
        )

    @classmethod
    @transaction.atomic
    def receive_advance(
        cls,
        *,
        customer_name,
        amount,
        source_type,
        source_id,
        payment_method=None,
        payment_account_code=None,
        customer=None,
        customer_phone="",
        source_reference="",
        received_date=None,
        actor=None,
    ):
        """
        Record a confirmed customer payment as a liability.

        For Ecommerce use source_type="ECOMMERCE_CHECKOUT" and use the
        checkout primary key as source_id. A repeated call for the same
        source returns the original advance without posting again.
        """
        customer_name = cls._clean_required(
            customer_name,
            "customer_name",
        )
        source_type = cls._clean_required(
            source_type,
            "source_type",
        ).upper()
        source_id = cls._clean_required(source_id, "source_id")
        amount = cls._amount(amount)

        existing = (
            CustomerAdvance.objects
            .select_for_update()
            .filter(
                source_type=source_type,
                source_id=source_id,
            )
            .first()
        )
        if existing is not None:
            if existing.amount != amount:
                raise ValidationError(
                    "This payment source already belongs to an advance "
                    f"of {existing.amount} {existing.currency}."
                )
            if (
                existing.receipt_entry_id
                and existing.receipt_entry.status == JournalEntry.POSTED
            ):
                return existing, False
            raise ValidationError(
                "An incomplete customer advance already exists for "
                "this payment source."
            )

        cash_account = cls._payment_account(
            payment_method=payment_method,
            account_code=payment_account_code,
        )
        advances_account = cls._account(
            cls.CUSTOMER_ADVANCES_ACCOUNT
        )

        advance = CustomerAdvance(
            customer=customer,
            customer_name=customer_name,
            customer_phone=(customer_phone or "").strip(),
            source_type=source_type,
            source_id=source_id,
            source_reference=(source_reference or "").strip(),
            amount=amount,
            status=CustomerAdvance.PENDING,
            created_by=cls._user(actor),
        )
        advance.full_clean()
        advance.save()

        entry, created = GeneralLedgerService.create_and_post(
            description=(
                f"Customer advance received from {customer_name}"
            ),
            lines=[
                {
                    "account": cash_account,
                    "debit": amount,
                    "description": (
                        f"Payment received — {advance.reference}"
                    ),
                },
                {
                    "account": advances_account,
                    "credit": amount,
                    "description": (
                        f"Customer advance liability — {advance.reference}"
                    ),
                },
            ],
            entry_date=received_date or timezone.localdate(),
            business_unit="",
            source_type="CUSTOMER_ADVANCE_RECEIPT",
            source_id=str(advance.pk),
            source_reference=(
                advance.source_reference or advance.reference
            ),
            source_key=(
                f"CUSTOMER_ADVANCE_RECEIPT:"
                f"{source_type}:{source_id}"
            ),
            actor=actor,
        )
        if not created:
            raise ValidationError(
                "The receipt journal already exists without its advance."
            )

        advance.receipt_entry = entry
        advance.received_at = timezone.now()
        advance.status = CustomerAdvance.AVAILABLE
        advance.save(
            update_fields=[
                "receipt_entry",
                "received_at",
                "status",
                "updated_at",
            ]
        )

        cls._dispatch(
            event_code="FINANCE_CUSTOMER_ADVANCE_RECEIVED",
            advance=advance,
            actor=actor,
            title="Customer Advance Received",
            message=(
                f"{amount} RWF was received from {customer_name} "
                f"as advance {advance.reference}."
            ),
            metadata={
                "journal_entry_id": entry.pk,
                "payment_account_code": cash_account.code,
            },
        )
        return advance, True

    @classmethod
    @transaction.atomic
    def apply_to_revenue(
        cls,
        *,
        advance,
        amount,
        business_unit,
        source_type,
        source_id,
        source_reference="",
        application_date=None,
        actor=None,
    ):
        """
        Recognize earned revenue after the related goods/services are
        delivered or otherwise fulfilled.
        """
        if not isinstance(advance, CustomerAdvance) or not advance.pk:
            raise ValidationError(
                "A saved customer advance is required."
            )

        amount = cls._amount(amount)
        source_type = cls._clean_required(
            source_type,
            "source_type",
        ).upper()
        source_id = cls._clean_required(source_id, "source_id")
        business_unit, revenue_account = cls._revenue_account(
            business_unit
        )

        advance = (
            CustomerAdvance.objects
            .select_for_update()
            .get(pk=advance.pk)
        )
        if advance.status in {
            CustomerAdvance.PENDING,
            CustomerAdvance.CANCELLED,
            CustomerAdvance.REFUNDED,
        }:
            raise ValidationError(
                f"Advance {advance.reference} cannot be applied "
                f"while it is {advance.get_status_display()}."
            )

        advances_account = cls._account(
            cls.CUSTOMER_ADVANCES_ACCOUNT
        )
        source_key = (
            f"CUSTOMER_ADVANCE_APPLICATION:{advance.pk}:"
            f"{source_type}:{source_id}"
        )

        existing_entry = JournalEntry.objects.filter(
            source_key=source_key
        ).first()
        if existing_entry is not None:
            if existing_entry.status != JournalEntry.POSTED:
                raise ValidationError(
                    "An incomplete application journal already exists."
                )
            return existing_entry, False

        if amount > advance.available_amount:
            raise ValidationError(
                {
                    "amount": (
                        f"Only {advance.available_amount} "
                        f"{advance.currency} remains available."
                    )
                }
            )

        entry, created = GeneralLedgerService.create_and_post(
            description=(
                f"Apply {advance.reference} to "
                f"{business_unit.title()} revenue"
            ),
            lines=[
                {
                    "account": advances_account,
                    "debit": amount,
                    "description": (
                        f"Release advance liability — {advance.reference}"
                    ),
                },
                {
                    "account": revenue_account,
                    "credit": amount,
                    "description": (
                        f"Revenue earned — "
                        f"{source_reference or source_id}"
                    ),
                },
            ],
            entry_date=application_date or timezone.localdate(),
            business_unit=business_unit,
            source_type=source_type,
            source_id=source_id,
            source_reference=(source_reference or "").strip(),
            source_key=source_key,
            actor=actor,
        )

        if created:
            advance.applied_amount += amount
            cls._set_status(advance)
            advance.full_clean()
            advance.save(
                update_fields=[
                    "applied_amount",
                    "status",
                    "updated_at",
                ]
            )
            cls._dispatch(
                event_code="FINANCE_CUSTOMER_ADVANCE_APPLIED",
                advance=advance,
                actor=actor,
                title="Customer Advance Applied",
                message=(
                    f"{amount} RWF from {advance.reference} was "
                    f"recognized as {business_unit.title()} revenue."
                ),
                metadata={
                    "journal_entry_id": entry.pk,
                    "business_unit": business_unit,
                    "revenue_account_code": revenue_account.code,
                },
            )

        return entry, created

    @classmethod
    @transaction.atomic
    def refund_advance(
        cls,
        *,
        advance,
        amount,
        source_id,
        reason,
        payment_account_code=None,
        refund_date=None,
        actor=None,
    ):
        """
        Refund an unused advance. By default the refund uses the same
        asset account that received the original payment.
        """
        if not isinstance(advance, CustomerAdvance) or not advance.pk:
            raise ValidationError(
                "A saved customer advance is required."
            )

        amount = cls._amount(amount)
        source_id = cls._clean_required(source_id, "source_id")
        reason = cls._clean_required(reason, "reason")

        advance = (
            CustomerAdvance.objects
            .select_for_update()
            .get(pk=advance.pk)
        )
        if advance.status in {
            CustomerAdvance.PENDING,
            CustomerAdvance.CANCELLED,
            CustomerAdvance.REFUNDED,
        }:
            raise ValidationError(
                f"Advance {advance.reference} cannot be refunded "
                f"while it is {advance.get_status_display()}."
            )

        source_key = (
            f"CUSTOMER_ADVANCE_REFUND:{advance.pk}:{source_id}"
        )
        existing_entry = JournalEntry.objects.filter(
            source_key=source_key
        ).first()
        if existing_entry is not None:
            if existing_entry.status != JournalEntry.POSTED:
                raise ValidationError(
                    "An incomplete refund journal already exists."
                )
            return existing_entry, False

        if amount > advance.available_amount:
            raise ValidationError(
                {
                    "amount": (
                        f"Only {advance.available_amount} "
                        f"{advance.currency} is refundable."
                    )
                }
            )

        cash_account = (
            cls._payment_account(account_code=payment_account_code)
            if payment_account_code
            else cls._receipt_cash_account(advance)
        )
        advances_account = cls._account(
            cls.CUSTOMER_ADVANCES_ACCOUNT
        )

        entry, created = GeneralLedgerService.create_and_post(
            description=(
                f"Refund customer advance {advance.reference}: {reason}"
            ),
            lines=[
                {
                    "account": advances_account,
                    "debit": amount,
                    "description": (
                        f"Reduce advance liability — {advance.reference}"
                    ),
                },
                {
                    "account": cash_account,
                    "credit": amount,
                    "description": (
                        f"Customer refund — {reason}"
                    ),
                },
            ],
            entry_date=refund_date or timezone.localdate(),
            business_unit="",
            source_type="CUSTOMER_ADVANCE_REFUND",
            source_id=source_id,
            source_reference=advance.reference,
            source_key=source_key,
            actor=actor,
        )

        if created:
            advance.refunded_amount += amount
            cls._set_status(advance)
            advance.full_clean()
            advance.save(
                update_fields=[
                    "refunded_amount",
                    "status",
                    "updated_at",
                ]
            )
            cls._dispatch(
                event_code="FINANCE_CUSTOMER_ADVANCE_REFUNDED",
                advance=advance,
                actor=actor,
                title="Customer Advance Refunded",
                message=(
                    f"{amount} RWF from {advance.reference} "
                    "was refunded."
                ),
                metadata={
                    "journal_entry_id": entry.pk,
                    "payment_account_code": cash_account.code,
                    "reason": reason,
                },
            )

        return entry, created

    @classmethod
    @transaction.atomic
    def cancel_pending(cls, *, advance, reason):
        """
        Cancel an unposted placeholder only. Posted advances must be
        refunded or corrected by journal entries.
        """
        if not isinstance(advance, CustomerAdvance) or not advance.pk:
            raise ValidationError(
                "A saved customer advance is required."
            )
        cls._clean_required(reason, "reason")

        advance = CustomerAdvance.objects.select_for_update().get(
            pk=advance.pk
        )
        if advance.status != CustomerAdvance.PENDING:
            raise ValidationError(
                "Only a pending, unposted advance can be cancelled."
            )
        if advance.receipt_entry_id:
            raise ValidationError(
                "A posted advance cannot be cancelled; refund it instead."
            )

        advance.status = CustomerAdvance.CANCELLED
        advance.save(update_fields=["status", "updated_at"])
        return advance
