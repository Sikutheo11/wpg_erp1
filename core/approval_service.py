from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import ApprovalRequest
from .workflow_service import WorkflowService
from .workflow import WorkflowRegistry
from .event_engine import EventEngine


class ApprovalService:
    """
    WPG BOS Approval Engine.

    Used when a workflow step requires approval.
    """

    @staticmethod
    def get_object_identity(obj):
        return {
            "object_app": obj._meta.app_label,
            "object_model": obj._meta.model_name,
            "object_id": str(obj.pk),
        }

    @staticmethod
    def has_pending_request(obj, workflow_code, to_step):
        identity = ApprovalService.get_object_identity(obj)

        return ApprovalRequest.objects.filter(
            workflow_code=workflow_code,
            object_app=identity["object_app"],
            object_model=identity["object_model"],
            object_id=identity["object_id"],
            to_step=to_step,
            status="PENDING",
        ).exists()

    @staticmethod
    @transaction.atomic
    def request_approval(
        obj,
        workflow_code,
        to_step,
        requested_by=None,
        reason=""
    ):
        from_step = WorkflowService.get_current_step(obj)

        if not WorkflowRegistry.requires_approval(
            workflow_code,
            to_step
        ):
            raise ValidationError(
                f"Step {to_step} does not require approval."
            )

        if ApprovalService.has_pending_request(
            obj,
            workflow_code,
            to_step
        ):
            raise ValidationError(
                "There is already a pending approval request for this step."
            )

        identity = ApprovalService.get_object_identity(obj)

        return ApprovalRequest.objects.create(
            workflow_code=workflow_code,
            object_app=identity["object_app"],
            object_model=identity["object_model"],
            object_id=identity["object_id"],
            from_step=from_step,
            to_step=to_step,
            requested_by=requested_by,
            reason=reason,
            status="PENDING",
        )

    @staticmethod
    @transaction.atomic
    def reject(approval_request, approved_by=None, reason=""):

        if approval_request.status != "PENDING":
            raise ValidationError(
                "Only pending approval requests can be rejected."
            )

        approval_request.status = "REJECTED"
        approval_request.approved_by = approved_by
        approval_request.reason = reason
        approval_request.decided_at = timezone.now()
        approval_request.save()

        return approval_request

    @staticmethod
    def get_target_object(approval_request):
        from django.apps import apps

        model = apps.get_model(
            approval_request.object_app,
            approval_request.object_model
        )

        if not model:
            raise ValidationError(
                "Target model not found."
            )

        return model.objects.get(
            pk=approval_request.object_id
        )
    
    @staticmethod
    @transaction.atomic
    def approve(approval_request, approved_by=None, note=""):

        if approval_request.status != "PENDING":
            raise ValidationError(
                "Only pending approval requests can be approved."
            )

        obj = ApprovalService.get_target_object(
            approval_request
        )

        WorkflowService.move(
            obj=obj,
            workflow_code=approval_request.workflow_code,
            to_step=approval_request.to_step,
            user=approved_by,
            note=note or "Approved via Approval Engine",
        )

        approval_request.status = "APPROVED"
        approval_request.approved_by = approved_by
        approval_request.decided_at = timezone.now()
        approval_request.save()

        EventEngine.dispatch(
            event_code="APPROVAL_APPROVED",
            actor=approved_by,
            obj=obj,
            title="Approval Approved",
            message=f"{approval_request.object_model} approved to {approval_request.to_step}",
            level="SUCCESS",
            metadata={
                "approval_request_id": approval_request.id,
                "workflow_code": approval_request.workflow_code,
                "from_step": approval_request.from_step,
                "to_step": approval_request.to_step,
            },
            notify_users=[
                approval_request.requested_by,
            ],
            notify_groups=[
                "CEO",
                "Administrator",
            ],
            notify_owner=True,
        )

        return approval_request

    @staticmethod
    @transaction.atomic
    def reject(approval_request, approved_by=None, reason=""):

        if approval_request.status != "PENDING":
            raise ValidationError(
                "Only pending approval requests can be rejected."
            )

        obj = ApprovalService.get_target_object(
            approval_request
        )

        approval_request.status = "REJECTED"
        approval_request.approved_by = approved_by
        approval_request.reason = reason
        approval_request.decided_at = timezone.now()
        approval_request.save()

        EventEngine.dispatch(
            event_code="APPROVAL_REJECTED",
            actor=approved_by,
            obj=obj,
            title="Approval Rejected",
            message=f"{approval_request.object_model} rejected for {approval_request.to_step}",
            level="DANGER",
            metadata={
                "approval_request_id": approval_request.id,
                "workflow_code": approval_request.workflow_code,
                "from_step": approval_request.from_step,
                "to_step": approval_request.to_step,
                "reason": reason,
            },
            notify_users=[
                approval_request.requested_by,
            ],
            notify_groups=[
                "CEO",
                "Administrator",
            ],
            notify_owner=True,
        )

        return approval_request