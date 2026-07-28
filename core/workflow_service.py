from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .event_engine import EventEngine
from .models import WorkflowTransition
from .permissions import PermissionService
from .workflow import WorkflowRegistry


class WorkflowService:
    """
    WPG BOS Enterprise Workflow Service.

    Responsibilities:
    - resolve the current workflow step;
    - validate explicit workflow transitions;
    - enforce role/feature permissions in the backend;
    - validate required notes or reasons;
    - update the business object state;
    - save workflow transition history;
    - dispatch workflow events;
    - expose transitions available to a user.
    """

    @staticmethod
    def _user(actor):
        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(actor, "user", None)

    @staticmethod
    def get_current_step(obj):
        if obj is None:
            raise ValidationError("Workflow object is required.")

        if hasattr(obj, "workflow_step"):
            return getattr(obj, "workflow_step", "") or ""

        if hasattr(obj, "status"):
            return getattr(obj, "status", "") or ""

        raise ValidationError(
            "This object has no workflow_step or status field."
        )

    @staticmethod
    def get_state_field_name(obj):
        if hasattr(obj, "workflow_step"):
            return "workflow_step"

        if hasattr(obj, "status"):
            return "status"

        raise ValidationError(
            "This object has no workflow_step or status field."
        )

    @staticmethod
    def set_current_step(obj, step_code):
        if not step_code:
            raise ValidationError("Target workflow step is required.")

        field_name = WorkflowService.get_state_field_name(obj)
        setattr(obj, field_name, step_code)
        return obj

    @staticmethod
    def get_transition(*, workflow_code, from_step, to_step):
        transition = WorkflowRegistry.get_transition(
            workflow_code,
            from_step,
            to_step,
        )

        if transition is None:
            raise ValidationError(
                f"Invalid workflow move: {from_step or '[empty]'} → {to_step}"
            )

        return transition

    @staticmethod
    def validate_note(*, transition, note):
        note = (note or "").strip()

        if transition.requires_note and not note:
            raise ValidationError(
                f"A note or reason is required to perform '{transition.name}'."
            )

        return note

    @staticmethod
    def user_can_transition(*, user, transition):
        resolved_user = WorkflowService._user(user)

        if not transition.feature_code:
            return True

        return PermissionService.user_can_access_feature(
            resolved_user,
            transition.feature_code,
            action=transition.permission_action or "edit",
        )

    @staticmethod
    def require_transition_permission(*, user, transition):
        if WorkflowService.user_can_transition(
            user=user,
            transition=transition,
        ):
            return True

        raise PermissionDenied(
            "You do not have permission to perform "
            f"'{transition.name or transition.to_step}'."
        )

    @staticmethod
    def _dispatch_transition_event(
        *,
        obj,
        workflow_code,
        transition,
        actor,
        from_step,
        to_step,
        note,
        history,
    ):
        if not transition.event_code:
            return None

        object_label = (
            obj._meta.verbose_name
            if hasattr(obj, "_meta")
            else obj.__class__.__name__
        )

        return EventEngine.dispatch(
            event_code=transition.event_code,
            actor=WorkflowService._user(actor),
            obj=obj,
            title=transition.name or "Workflow Transition",
            message=(
                f"{object_label.title()} {obj} moved from "
                f"{from_step or '[empty]'} to {to_step}."
            ),
            level=transition.event_level or "INFO",
            metadata={
                "workflow_code": workflow_code,
                "workflow_transition_id": history.pk if history else None,
                "object_app": obj._meta.app_label,
                "object_model": obj._meta.model_name,
                "object_id": str(obj.pk),
                "from_step": from_step,
                "to_step": to_step,
                "transition_name": transition.name,
                "feature_code": transition.feature_code,
                "permission_action": transition.permission_action,
                "is_approval": transition.is_approval,
                "note": note,
            },
            notify_groups=[],
            notify_owner=True,
        )

    @staticmethod
    @transaction.atomic
    def move(
        obj,
        workflow_code,
        to_step,
        user=None,
        note="",
        *,
        check_permission=True,
        dispatch_event=True,
        save_kwargs=None,
    ):
        if obj is None:
            raise ValidationError("Workflow object is required.")

        if not getattr(obj, "pk", None):
            raise ValidationError(
                "The workflow object must be saved before it can move."
            )

        from_step = WorkflowService.get_current_step(obj)

        transition = WorkflowService.get_transition(
            workflow_code=workflow_code,
            from_step=from_step,
            to_step=to_step,
        )

        note = WorkflowService.validate_note(
            transition=transition,
            note=note,
        )

        if check_permission:
            WorkflowService.require_transition_permission(
                user=user,
                transition=transition,
            )

        state_field = WorkflowService.get_state_field_name(obj)
        WorkflowService.set_current_step(obj, to_step)

        if hasattr(obj, "full_clean"):
            obj.full_clean()

        save_kwargs = dict(save_kwargs or {})

        if "update_fields" not in save_kwargs:
            update_fields = [state_field]

            try:
                obj._meta.get_field("updated_at")
            except Exception:
                pass
            else:
                update_fields.append("updated_at")

            save_kwargs["update_fields"] = update_fields

        obj.save(**save_kwargs)

        history = WorkflowTransition.objects.create(
            workflow_code=workflow_code,
            object_app=obj._meta.app_label,
            object_model=obj._meta.model_name,
            object_id=str(obj.pk),
            from_step=from_step,
            to_step=to_step,
            moved_by=WorkflowService._user(user),
            note=note,
        )

        if dispatch_event:
            WorkflowService._dispatch_transition_event(
                obj=obj,
                workflow_code=workflow_code,
                transition=transition,
                actor=user,
                from_step=from_step,
                to_step=to_step,
                note=note,
                history=history,
            )

        return obj

    @staticmethod
    @transaction.atomic
    def next(
        obj,
        workflow_code,
        user=None,
        note="",
        *,
        check_permission=True,
        dispatch_event=True,
    ):
        current_step = WorkflowService.get_current_step(obj)

        transitions = WorkflowRegistry.get_available_transitions(
            workflow_code,
            current_step,
        )

        if not transitions:
            raise ValidationError(
                f"No workflow transition is available from {current_step}."
            )

        transition = transitions[0]

        return WorkflowService.move(
            obj=obj,
            workflow_code=workflow_code,
            to_step=transition.to_step,
            user=user,
            note=note,
            check_permission=check_permission,
            dispatch_event=dispatch_event,
        )

    @staticmethod
    def get_available_transitions(obj, workflow_code, user=None):
        current_step = WorkflowService.get_current_step(obj)

        transitions = WorkflowRegistry.get_available_transitions(
            workflow_code,
            current_step,
        )

        return [
            transition
            for transition in transitions
            if WorkflowService.user_can_transition(
                user=user,
                transition=transition,
            )
        ]

    @staticmethod
    def get_available_action_map(obj, workflow_code, user=None):
        return {
            transition.to_step: transition
            for transition in WorkflowService.get_available_transitions(
                obj,
                workflow_code,
                user=user,
            )
        }

    @staticmethod
    def can_user_move(*, obj, workflow_code, to_step, user=None):
        from_step = WorkflowService.get_current_step(obj)

        transition = WorkflowRegistry.get_transition(
            workflow_code,
            from_step,
            to_step,
        )

        if transition is None:
            return False

        return WorkflowService.user_can_transition(
            user=user,
            transition=transition,
        )

    @staticmethod
    def history(obj):
        if obj is None or not getattr(obj, "pk", None):
            return WorkflowTransition.objects.none()

        return (
            WorkflowTransition.objects
            .filter(
                object_app=obj._meta.app_label,
                object_model=obj._meta.model_name,
                object_id=str(obj.pk),
            )
            .select_related("moved_by")
            .order_by("-created_at", "-pk")
        )
