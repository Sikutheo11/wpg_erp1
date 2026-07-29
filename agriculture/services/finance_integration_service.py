from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine
from finance.models import Expense
from finance.services.expense_service import ExpenseService

from ..models import AgricultureOperation, FeedingRecord, HealthRecord


class AgricultureFinanceIntegrationService:
    """
    Posts Agriculture operating costs through the shared Finance Engine.

    Each source record receives a deterministic Finance reference. ExpenseService
    rejects duplicate references, while locking the Agriculture source record
    protects concurrent retries.
    """

    BUSINESS_UNIT = "AGRICULTURE"

    @staticmethod
    def _user(actor):
        if actor is None:
            return None
        if getattr(actor, "is_authenticated", False):
            return actor
        return getattr(actor, "user", None)

    @staticmethod
    def _saved(record, expected_model):
        if record is None or not isinstance(record, expected_model):
            raise ValidationError(
                f"A saved {expected_model.__name__} record is required."
            )
        if not record.pk:
            raise ValidationError(
                f"The {expected_model.__name__} record must be saved first."
            )

    @staticmethod
    def _expense_by_reference(reference):
        return (
            Expense.objects.filter(
                title__contains=f"[{reference}]",
            )
            .select_related("account")
            .order_by("pk")
            .first()
        )

    @classmethod
    def _update_operation_cost(
        cls,
        *,
        operation,
        amount,
        reference,
    ):
        if operation is None:
            raise ValidationError(
                "A Finance posting requires an Agriculture operation."
            )

        locked = AgricultureOperation.objects.select_for_update().get(
            pk=operation.pk
        )
        locked.actual_cost = (
            Decimal(str(locked.actual_cost)) + Decimal(str(amount))
        )
        locked.finance_reference = reference
        locked.finance_posted_at = timezone.now()
        locked.full_clean()
        locked.save(
            update_fields=[
                "actual_cost",
                "finance_reference",
                "finance_posted_at",
                "updated_at",
            ]
        )
        return locked

    @classmethod
    def _dispatch(
        cls,
        *,
        source,
        operation,
        expense,
        reference,
        actor,
    ):
        EventEngine.dispatch(
            event_code="AGRICULTURE_COST_POSTED",
            actor=cls._user(actor),
            obj=source,
            title="Agriculture Cost Posted",
            message=(
                f"{expense.amount} RWF from Agriculture record "
                f"#{source.pk} was posted to Finance."
            ),
            level="SUCCESS",
            metadata={
                "business_unit": cls.BUSINESS_UNIT,
                "source_model": source._meta.model_name,
                "source_id": source.pk,
                "operation_id": operation.pk,
                "operation_code": operation.code,
                "expense_id": expense.pk,
                "account_id": expense.account_id,
                "amount": str(expense.amount),
                "reference": reference,
            },
            notify_groups=[
                "Finance Manager",
                "Agriculture Manager",
            ],
            notify_owner=True,
        )

    @classmethod
    @transaction.atomic
    def post_feeding_cost(
        cls,
        *,
        feeding_record,
        account,
        actor=None,
    ):
        cls._saved(feeding_record, FeedingRecord)
        # Lock only the source row; operation is nullable and must not be part
        # of a PostgreSQL FOR UPDATE outer join.
        record = FeedingRecord.objects.select_for_update().get(
            pk=feeding_record.pk
        )

        if record.operation_id is None:
            raise ValidationError(
                "The feeding record must be linked to an Agriculture operation."
            )

        amount = Decimal(str(record.total_cost))
        if amount <= 0:
            raise ValidationError(
                "The feeding cost must be greater than zero before posting."
            )

        reference = f"AGRI-FEED-{record.pk}"
        existing = cls._expense_by_reference(reference)
        if existing is not None:
            return {
                "expense": existing,
                "operation": record.operation,
                "transaction": None,
                "reference": reference,
                "created": False,
            }

        result = ExpenseService.record_operating_expense(
            account=account,
            title=(
                f"Feed consumed by flock {record.flock.code}: "
                f"{record.quantity_kg} kg of {record.feed_product.name}"
            ),
            amount=amount,
            reference=reference,
            actor=actor,
        )

        operation = cls._update_operation_cost(
            operation=record.operation,
            amount=amount,
            reference=reference,
        )
        cls._dispatch(
            source=record,
            operation=operation,
            expense=result["expense"],
            reference=reference,
            actor=actor,
        )
        return {
            **result,
            "operation": operation,
            "reference": reference,
            "created": True,
        }

    @classmethod
    @transaction.atomic
    def post_health_cost(
        cls,
        *,
        health_record,
        account,
        actor=None,
    ):
        cls._saved(health_record, HealthRecord)
        # Lock only the source row; operation is nullable and is resolved
        # lazily inside this transaction.
        record = HealthRecord.objects.select_for_update().get(
            pk=health_record.pk
        )

        if record.operation_id is None:
            raise ValidationError(
                "The health record must be linked to an Agriculture operation."
            )

        amount = Decimal(str(record.cost))
        if amount <= 0:
            raise ValidationError(
                "The health cost must be greater than zero before posting."
            )

        reference = f"AGRI-HEALTH-{record.pk}"
        existing = cls._expense_by_reference(reference)
        if existing is not None:
            return {
                "expense": existing,
                "operation": record.operation,
                "transaction": None,
                "reference": reference,
                "created": False,
            }

        result = ExpenseService.record_operating_expense(
            account=account,
            title=(
                f"{record.get_record_type_display()} for flock "
                f"{record.flock.code}: {record.condition_or_vaccine}"
            ),
            amount=amount,
            reference=reference,
            actor=actor,
        )

        operation = cls._update_operation_cost(
            operation=record.operation,
            amount=amount,
            reference=reference,
        )
        cls._dispatch(
            source=record,
            operation=operation,
            expense=result["expense"],
            reference=reference,
            actor=actor,
        )
        return {
            **result,
            "operation": operation,
            "reference": reference,
            "created": True,
        }
