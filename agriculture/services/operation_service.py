from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine
from core.workflow_service import WorkflowService

from ..models import AgricultureOperation


class AgricultureOperationService:
    """Application service for the Agriculture operation lifecycle."""

    WORKFLOW_CODE = AgricultureOperation.WORKFLOW_NAME
    BUSINESS_UNIT = AgricultureOperation.BUSINESS_UNIT

    @staticmethod
    def _authenticated_user(user):
        if user is not None and getattr(user, "is_authenticated", False):
            return user
        return None

    @classmethod
    def _generate_code(cls):
        prefix = timezone.localdate().strftime("AGR-%Y%m%d")

        while True:
            code = f"{prefix}-{uuid4().hex[:8].upper()}"
            if not AgricultureOperation.objects.filter(code=code).exists():
                return code

    @classmethod
    def _lock(cls, operation):
        if operation is None or not getattr(operation, "pk", None):
            raise ValidationError("A saved agriculture operation is required.")

        # Lock only the AgricultureOperation row. Joining nullable foreign
        # keys here makes PostgreSQL reject FOR UPDATE on the nullable side
        # of the generated outer joins.
        return AgricultureOperation.objects.select_for_update().get(
            pk=operation.pk
        )

    @classmethod
    def _validate_source_order(cls, source_order):
        if source_order is None:
            return

        if getattr(source_order, "business_unit", None) != cls.BUSINESS_UNIT:
            raise ValidationError(
                {
                    "source_order": (
                        "The source order must belong to the AGRICULTURE "
                        "business unit."
                    )
                }
            )

    @staticmethod
    def _validate_farm(farm):
        if farm is None or not getattr(farm, "pk", None):
            raise ValidationError({"farm": "A saved poultry farm is required."})

        if not farm.is_active:
            raise ValidationError(
                {"farm": "Operations cannot be created for an inactive farm."}
            )

    @classmethod
    def _dispatch(cls, event_code, operation, actor=None, **metadata):
        EventEngine.dispatch(
            event_code=event_code,
            actor=cls._authenticated_user(actor),
            obj=operation,
            title=f"Agriculture operation {operation.code}",
            message=(
                f"Agriculture operation {operation.code} triggered "
                f"{event_code}."
            ),
            level="INFO",
            metadata={
                "operation_id": operation.pk,
                "operation_code": operation.code,
                "operation_type": operation.operation_type,
                "status": operation.status,
                "farm_id": operation.farm_id,
                "source_order_id": operation.source_order_id,
                **metadata,
            },
        )

    @classmethod
    @transaction.atomic
    def create_operation(
        cls,
        *,
        operation_type,
        farm,
        actor=None,
        source_order=None,
        assigned_to=None,
        planned_start_date=None,
        planned_end_date=None,
        budget=Decimal("0.00"),
        notes="",
        code="",
    ):
        cls._validate_farm(farm)
        cls._validate_source_order(source_order)

        operation = AgricultureOperation(
            code=code.strip() if code else cls._generate_code(),
            operation_type=operation_type,
            farm=farm,
            source_order=source_order,
            assigned_to=assigned_to,
            planned_start_date=planned_start_date,
            planned_end_date=planned_end_date,
            budget=budget,
            notes=(notes or "").strip(),
            created_by=cls._authenticated_user(actor),
        )
        operation.full_clean()
        operation.save()

        cls._dispatch(
            "AGRICULTURE_OPERATION_CREATED",
            operation,
            actor,
        )
        return operation

    @classmethod
    def create_from_order(
        cls,
        *,
        order,
        farm,
        actor=None,
        assigned_to=None,
        planned_start_date=None,
        planned_end_date=None,
        budget=Decimal("0.00"),
        notes="",
    ):
        cls._validate_source_order(order)

        operation_type = (
            "RESTOCK"
            if order.order_type == "RESTOCK"
            else "ORDER_FULFILMENT"
        )

        return cls.create_operation(
            operation_type=operation_type,
            farm=farm,
            actor=actor,
            source_order=order,
            assigned_to=assigned_to,
            planned_start_date=planned_start_date,
            planned_end_date=planned_end_date,
            budget=budget,
            notes=notes,
        )

    @classmethod
    def _move(
        cls,
        *,
        operation,
        to_step,
        actor,
        note="",
        prepare=None,
        check_permission=True,
    ):
        with transaction.atomic():
            locked = cls._lock(operation)

            if prepare is not None:
                prepare(locked)

            WorkflowService.move(
                obj=locked,
                workflow_code=cls.WORKFLOW_CODE,
                to_step=to_step,
                user=actor,
                note=(note or "").strip(),
                check_permission=check_permission,
                dispatch_event=True,
            )
            locked.refresh_from_db()
            return locked

    @classmethod
    def submit(cls, *, operation, actor, note=""):
        return cls._move(
            operation=operation,
            to_step="PENDING",
            actor=actor,
            note=note,
        )

    @classmethod
    def approve(cls, *, operation, actor, note=""):
        def prepare(obj):
            obj.approved_by = cls._authenticated_user(actor)
            obj.approved_at = timezone.now()

        return cls._move(
            operation=operation,
            to_step="APPROVED",
            actor=actor,
            note=note,
            prepare=prepare,
        )

    @classmethod
    def return_for_correction(cls, *, operation, actor, note):
        return cls._move(
            operation=operation,
            to_step="DRAFT",
            actor=actor,
            note=note,
        )

    @classmethod
    def start(cls, *, operation, actor, note=""):
        def prepare(obj):
            if obj.actual_start_date is None:
                obj.actual_start_date = timezone.localdate()

        return cls._move(
            operation=operation,
            to_step="ACTIVE",
            actor=actor,
            note=note,
            prepare=prepare,
        )

    @classmethod
    def hold(cls, *, operation, actor, note):
        return cls._move(
            operation=operation,
            to_step="ON_HOLD",
            actor=actor,
            note=note,
        )

    @classmethod
    def resume(cls, *, operation, actor, note=""):
        return cls._move(
            operation=operation,
            to_step="ACTIVE",
            actor=actor,
            note=note,
        )

    @classmethod
    def complete(cls, *, operation, actor, note=""):
        def prepare(obj):
            obj.actual_end_date = obj.actual_end_date or timezone.localdate()

        return cls._move(
            operation=operation,
            to_step="COMPLETED",
            actor=actor,
            note=note,
            prepare=prepare,
        )

    @classmethod
    def cancel(cls, *, operation, actor, reason):
        reason = (reason or "").strip()
        if not reason:
            raise ValidationError({"reason": "A cancellation reason is required."})

        def prepare(obj):
            obj.cancellation_reason = reason

        return cls._move(
            operation=operation,
            to_step="CANCELLED",
            actor=actor,
            note=reason,
            prepare=prepare,
        )

    @classmethod
    @transaction.atomic
    def mark_finance_posted(
        cls,
        *,
        operation,
        finance_reference,
        actual_cost,
        actor=None,
    ):
        reference = (finance_reference or "").strip()
        if not reference:
            raise ValidationError(
                {"finance_reference": "A Finance reference is required."}
            )

        try:
            cost = Decimal(str(actual_cost))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValidationError(
                {"actual_cost": "Enter a valid operational cost."}
            ) from exc

        if cost < 0:
            raise ValidationError(
                {"actual_cost": "Operational cost cannot be negative."}
            )

        locked = cls._lock(operation)
        locked.finance_reference = reference
        locked.finance_posted_at = timezone.now()
        locked.actual_cost = cost
        locked.full_clean()
        locked.save(
            update_fields=[
                "finance_reference",
                "finance_posted_at",
                "actual_cost",
                "updated_at",
            ]
        )

        cls._dispatch(
            "AGRICULTURE_FINANCE_POSTED",
            locked,
            actor,
            finance_reference=reference,
            actual_cost=str(cost),
        )
        return locked

    @classmethod
    def available_actions(cls, *, operation, actor=None):
        return WorkflowService.get_available_action_map(
            operation,
            cls.WORKFLOW_CODE,
            user=actor,
        )

    @staticmethod
    def history(*, operation):
        return WorkflowService.history(operation)
