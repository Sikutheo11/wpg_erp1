from django.core.exceptions import ValidationError
from django.db import transaction

from .models import WorkflowTransition
from .workflow import WorkflowRegistry


class WorkflowService:
    """
    WPG BOS Workflow Service.

    Responsibilities:
    - validate workflow movement
    - move object from one step to another
    - save workflow history
    """

    @staticmethod
    def get_current_step(obj):
        return getattr(obj, "workflow_step", None) or getattr(obj, "status", "")

    @staticmethod
    def set_current_step(obj, step_code):
        if hasattr(obj, "workflow_step"):
            obj.workflow_step = step_code
        elif hasattr(obj, "status"):
            obj.status = step_code
        else:
            raise ValidationError(
                "This object has no workflow_step or status field."
            )

    @staticmethod
    @transaction.atomic
    def move(obj, workflow_code, to_step, user=None, note=""):
        from_step = WorkflowService.get_current_step(obj)

        if from_step:
            allowed = WorkflowRegistry.can_move_to(
                workflow_code,
                from_step,
                to_step,
            )

            if not allowed:
                raise ValidationError(
                    f"Invalid workflow move: {from_step} → {to_step}"
                )

        WorkflowService.set_current_step(obj, to_step)
        obj.save()

        WorkflowTransition.objects.create(
            workflow_code=workflow_code,
            object_app=obj._meta.app_label,
            object_model=obj._meta.model_name,
            object_id=str(obj.pk),
            from_step=from_step,
            to_step=to_step,
            moved_by=user,
            note=note,
        )

        return obj

    @staticmethod
    def next(obj, workflow_code, user=None, note=""):
        current_step = WorkflowService.get_current_step(obj)

        next_step = WorkflowRegistry.get_next_step(
            workflow_code,
            current_step,
        )

        return WorkflowService.move(
            obj=obj,
            workflow_code=workflow_code,
            to_step=next_step.code,
            user=user,
            note=note,
        )

    @staticmethod
    def history(obj):
        return WorkflowTransition.objects.filter(
            object_app=obj._meta.app_label,
            object_model=obj._meta.model_name,
            object_id=str(obj.pk),
        )