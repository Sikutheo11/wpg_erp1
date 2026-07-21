from django.core.exceptions import ValidationError
from django.db import transaction

from core.workflow_service import WorkflowService
from core.approval_service import ApprovalService
from core.event_engine import EventEngine

from furniture.models import ProductionTimeline


class FurnitureWorkflowService:
    """
    Furniture Workflow Integration.

    Connects Furniture module with:
        - Workflow Engine
        - Approval Engine
        - Event Engine
    """

    # =====================================================
    # TIMELINE
    # =====================================================

    @staticmethod
    def timeline(
        production_job,
        action,
        from_status="",
        to_status="",
        performed_by=None,
        note="",
    ):

        return ProductionTimeline.objects.create(
            production_job=production_job,
            action=action,
            from_status=from_status,
            to_status=to_status,
            performed_by=performed_by,
            note=note,
        )

    # =====================================================
    # NEXT STEP
    # =====================================================

    @classmethod
    @transaction.atomic
    def next_step(
        cls,
        production_job,
        user=None,
        note="",
    ):

        old_status = production_job.status

        WorkflowService.next(
            obj=production_job,
            workflow_code="FURNITURE_PRODUCTION",
            user=user,
            note=note,
        )

        production_job.refresh_from_db()

        cls.timeline(
            production_job=production_job,
            action="Workflow moved",
            from_status=old_status,
            to_status=production_job.status,
            performed_by=getattr(user, "employee", None),
            note=note,
        )

        return production_job

    # =====================================================
    # REQUEST APPROVAL
    # =====================================================

    @staticmethod
    def request_approval(
        production_job,
        requested_by=None,
        reason="Approval required",
    ):

        return ApprovalService.request_approval(
            obj=production_job,
            workflow_code="FURNITURE_PRODUCTION",
            to_step="APPROVED",
            requested_by=requested_by,
            reason=reason,
        )

    # =====================================================
    # APPROVE
    # =====================================================

    @classmethod
    @transaction.atomic
    def approve(
        cls,
        approval_request,
        approved_by=None,
        note="",
    ):

        approval = ApprovalService.approve(
            approval_request=approval_request,
            approved_by=approved_by,
            note=note,
        )

        production_job = approval_request.content_object

        cls.timeline(
            production_job=production_job,
            action="Approval completed",
            from_status=approval_request.from_step,
            to_status=approval_request.to_step,
            performed_by=getattr(approved_by, "employee", None),
            note=note,
        )

        return approval

    # =====================================================
    # REJECT
    # =====================================================

    @classmethod
    @transaction.atomic
    def reject(
        cls,
        approval_request,
        rejected_by=None,
        reason="",
    ):

        approval = ApprovalService.reject(
            approval_request=approval_request,
            rejected_by=rejected_by,
            reason=reason,
        )

        production_job = approval_request.content_object

        cls.timeline(
            production_job=production_job,
            action="Approval rejected",
            from_status=approval_request.from_step,
            to_status=approval_request.from_step,
            performed_by=getattr(rejected_by, "employee", None),
            note=reason,
        )

        return approval

    # =====================================================
    # CANCEL
    # =====================================================

    @classmethod
    @transaction.atomic
    def cancel(
        cls,
        production_job,
        user=None,
        note="",
    ):

        if production_job.status == "DELIVERED":
            raise ValidationError(
                "Delivered jobs cannot be cancelled."
            )

        old_status = production_job.status

        production_job.status = "CANCELLED"
        production_job.save()

        cls.timeline(
            production_job=production_job,
            action="Workflow cancelled",
            from_status=old_status,
            to_status="CANCELLED",
            performed_by=getattr(user, "employee", None),
            note=note,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_WORKFLOW_CANCELLED",
            actor=user,
            obj=production_job,
            title="Production Cancelled",
            message=f"Production Job #{production_job.id} cancelled.",
            level="WARNING",
            notify_owner=True,
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
        )

        return production_job