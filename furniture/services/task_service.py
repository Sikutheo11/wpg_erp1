from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.event_engine import EventEngine

from furniture.models import (
    ProductionTask,
    ProductionTaskAssignment,
    ProductionTaskLog,
    ProductionChecklist,
    ProductionTimeline,
    ProductionTaskProgress,
)


class ProductionTaskService:
    """
    Business service for managing furniture production tasks.

    Handles:
    - task creation
    - worker assignment
    - status changes
    - progress updates
    - work logging
    - checklist validation
    - timeline events
    - notifications and audit events
    """

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _employee_from_user(user):
        if not user:
            return None

        return getattr(user, "employee", None)

    @staticmethod
    def _actor_from_employee(employee):
        if not employee:
            return None

        return getattr(employee, "user", None)

    @staticmethod
    def _log(
        task,
        action,
        employee=None,
        previous_status="",
        new_status="",
        hours_worked=Decimal("0.00"),
        progress_percentage=None,
        note="",
    ):
        return ProductionTaskLog.objects.create(
            task=task,
            action=action,
            employee=employee,
            previous_status=previous_status or "",
            new_status=new_status or "",
            hours_worked=hours_worked or Decimal("0.00"),
            progress_percentage=(
                task.progress_percentage
                if progress_percentage is None
                else progress_percentage
            ),
            note=note or "",
        )

    @staticmethod
    def _timeline(
        task,
        action,
        performed_by=None,
        note="",
    ):
        return ProductionTimeline.objects.create(
            production_job=task.production_job,
            action=action,
            from_status=task.production_job.status,
            to_status=task.production_job.status,
            performed_by=performed_by,
            note=note or "",
        )

    @classmethod
    def _dispatch(
        cls,
        event_code,
        task,
        title,
        message,
        actor=None,
        level="INFO",
        metadata=None,
        notify_users=None,
        notify_groups=None,
    ):
        normalized_users = []

        for recipient in notify_users or []:
            if recipient is None:
                continue

            # Employee -> User
            if hasattr(recipient, "user"):
                recipient = recipient.user

            normalized_users.append(recipient)

        return EventEngine.dispatch(
            event_code=event_code,
            actor=actor,
            obj=task,
            title=title,
            message=message,
            level=level,
            metadata=metadata or {},
            notify_users=normalized_users,
            notify_groups=notify_groups or [
                "Furniture Manager",
                "Production Supervisor",
            ],
            notify_owner=True,
        )
    

    @staticmethod
    def _validate_progress(progress_percentage):
        if progress_percentage < 0 or progress_percentage > 100:
            raise ValidationError(
                "Progress percentage must be between 0 and 100."
            )

    @staticmethod
    def _ensure_required_checklist_complete(task):
        incomplete_required = task.checklist_items.filter(
            is_required=True,
            is_completed=False,
        ).exists()

        if incomplete_required:
            raise ValidationError(
                "All required checklist items must be completed first."
            )

    # =====================================================
    # CREATE TASK
    # =====================================================

    @classmethod
    @transaction.atomic
    def create_task(
        cls,
        production_job,
        name,
        task_type="OTHER",
        description="",
        sequence=1,
        priority="NORMAL",
        assigned_to=None,
        planned_hours=Decimal("0.00"),
        planned_start=None,
        planned_end=None,
        created_by=None,
        checklist_items=None,
    ):
        if not name:
            raise ValidationError("Task name is required.")

        if planned_hours < 0:
            raise ValidationError(
                "Planned hours cannot be negative."
            )

        if (
            planned_start
            and planned_end
            and planned_end < planned_start
        ):
            raise ValidationError(
                "Planned end cannot be before planned start."
            )

        task = ProductionTask.objects.create(
            production_job=production_job,
            name=name,
            task_type=task_type,
            description=description,
            sequence=sequence,
            status="READY" if assigned_to else "PENDING",
            priority=priority,
            assigned_to=assigned_to,
            planned_hours=planned_hours,
            planned_start=planned_start,
            planned_end=planned_end,
            created_by=created_by,
        )

        cls._log(
            task=task,
            action="CREATED",
            employee=created_by,
            new_status=task.status,
            note="Production task created.",
        )

        cls._timeline(
            task=task,
            action=f"Task created: {task.name}",
            performed_by=created_by,
            note=f"Sequence {task.sequence}",
        )

        if assigned_to:
            ProductionTaskAssignment.objects.create(
                task=task,
                employee=assigned_to,
                assigned_by=created_by,
                is_active=True,
            )

            cls._log(
                task=task,
                action="ASSIGNED",
                employee=created_by,
                new_status=task.status,
                note=f"Assigned to {assigned_to}.",
            )

        for index, item in enumerate(
            checklist_items or [],
            start=1,
        ):
            if isinstance(item, str):
                title = item
                required = True
            else:
                title = item.get("title", "")
                required = item.get("is_required", True)

            if title:
                ProductionChecklist.objects.create(
                    task=task,
                    title=title,
                    is_required=required,
                    order=index,
                )

        cls._dispatch(
            event_code="FURNITURE_TASK_CREATED",
            task=task,
            actor=cls._actor_from_employee(created_by),
            title="Production Task Created",
            message=(
                f"Task '{task.name}' was created for "
                f"production job #{production_job.id}."
            ),
            metadata={
                "task_id": task.id,
                "production_job_id": production_job.id,
                "task_type": task.task_type,
                "sequence": task.sequence,
            },
            notify_users=[
                cls._actor_from_employee(assigned_to),
            ] if assigned_to else [],
        )

        return task

    # =====================================================
    # ASSIGN WORKER
    # =====================================================

    @classmethod
    @transaction.atomic
    def assign_worker(
        cls,
        task,
        employee,
        assigned_by=None,
        note="",
    ):
        if task.status in {
            "COMPLETED",
            "CANCELLED",
        }:
            raise ValidationError(
                "Completed or cancelled tasks cannot be reassigned."
            )

        ProductionTaskAssignment.objects.filter(
            task=task,
            is_active=True,
        ).update(
            is_active=False,
            released_at=timezone.now(),
        )

        previous_employee = task.assigned_to
        previous_status = task.status

        task.assigned_to = employee

        if task.status == "PENDING":
            task.status = "READY"

        task.save(
            update_fields=[
                "assigned_to",
                "status",
                "updated_at",
            ]
        )

        ProductionTaskAssignment.objects.create(
            task=task,
            employee=employee,
            assigned_by=assigned_by,
            is_active=True,
            note=note,
        )

        cls._log(
            task=task,
            action="ASSIGNED",
            employee=assigned_by,
            previous_status=previous_status,
            new_status=task.status,
            note=(
                note
                or f"Assigned from {previous_employee or 'nobody'} "
                f"to {employee}."
            ),
        )

        cls._timeline(
            task=task,
            action=f"Task assigned: {task.name}",
            performed_by=assigned_by,
            note=f"Assigned to {employee}.",
        )

        cls._dispatch(
            event_code="FURNITURE_TASK_ASSIGNED",
            task=task,
            actor=cls._actor_from_employee(assigned_by),
            title="Production Task Assigned",
            message=f"Task '{task.name}' assigned to {employee}.",
            metadata={
                "task_id": task.id,
                "production_job_id": task.production_job_id,
                "employee_id": employee.id,
            },
            notify_users=[
                cls._actor_from_employee(employee),
            ],
        )

        return task

    # =====================================================
    # START TASK
    # =====================================================

    @classmethod
    @transaction.atomic
    def start_task(
        cls,
        task,
        employee=None,
        note="",
    ):
        if task.status not in {
            "PENDING",
            "READY",
            "PAUSED",
        }:
            raise ValidationError(
                "Only pending, ready or paused tasks can be started."
            )

        if task.assigned_to and employee:
            if task.assigned_to_id != employee.id:
                raise ValidationError(
                    "This task is assigned to another employee."
                )

        previous_status = task.status

        task.status = "IN_PROGRESS"

        if not task.started_at:
            task.started_at = timezone.now()

        task.save(
            update_fields=[
                "status",
                "started_at",
                "updated_at",
            ]
        )

        action = (
            "RESUMED"
            if previous_status == "PAUSED"
            else "STARTED"
        )

        cls._log(
            task=task,
            action=action,
            employee=employee,
            previous_status=previous_status,
            new_status=task.status,
            note=note or "Task started.",
        )

        cls._timeline(
            task=task,
            action=f"Task started: {task.name}",
            performed_by=employee,
            note=note,
        )

        cls._dispatch(
            event_code="FURNITURE_TASK_STARTED",
            task=task,
            actor=cls._actor_from_employee(employee),
            title="Production Task Started",
            message=f"Task '{task.name}' is now in progress.",
            metadata={
                "task_id": task.id,
                "production_job_id": task.production_job_id,
            },
            level="INFO",
        )

        return task

    # =====================================================
    # UPDATE PROGRESS
    # =====================================================

    @classmethod
    @transaction.atomic
    def update_progress(
        cls,
        task,
        progress_percentage,
        employee=None,
        hours_worked=Decimal("0.00"),
        image=None,
        note="",
    ):
        cls._validate_progress(progress_percentage)

        if task.status in {
            "COMPLETED",
            "CANCELLED",
        }:
            raise ValidationError(
                "Completed or cancelled tasks cannot be updated."
            )

        if hours_worked is None:
            hours_worked = Decimal("0.00")

        if not isinstance(hours_worked, Decimal):
            hours_worked = Decimal(str(hours_worked))

        if hours_worked < 0:
            raise ValidationError(
                "Hours worked cannot be negative."
            )

        if progress_percentage < task.progress_percentage:
            raise ValidationError(
                "Task progress cannot be lower than its current progress."
            )

        previous_status = task.status

        if progress_percentage > 0 and task.status in {
            "PENDING",
            "READY",
            "PAUSED",
            "BLOCKED",
        }:
            task.status = "IN_PROGRESS"

            if not task.started_at:
                task.started_at = timezone.now()

        task.progress_percentage = progress_percentage
        task.actual_hours += hours_worked

        task.save(
            update_fields=[
                "status",
                "started_at",
                "progress_percentage",
                "actual_hours",
                "updated_at",
            ]
        )

        progress_update = ProductionTaskProgress.objects.create(
            task=task,
            employee=employee,
            progress_percentage=progress_percentage,
            hours_worked=hours_worked,
            image=image,
            note=note or "",
        )

        cls._log(
            task=task,
            action="PROGRESS_UPDATED",
            employee=employee,
            previous_status=previous_status,
            new_status=task.status,
            hours_worked=hours_worked,
            progress_percentage=progress_percentage,
            note=note,
        )

        cls._timeline(
            task=task,
            action=f"Task progress updated: {task.name}",
            performed_by=employee,
            note=(
                f"{progress_percentage}% complete. "
                f"{note or ''}"
            ).strip(),
        )

        cls._dispatch(
            event_code="FURNITURE_TASK_PROGRESS_UPDATED",
            task=task,
            actor=cls._actor_from_employee(employee),
            title="Task Progress Updated",
            message=(
                f"Task '{task.name}' progress updated "
                f"to {progress_percentage}%."
            ),
            metadata={
                "task_id": task.id,
                "production_job_id": task.production_job_id,
                "progress_update_id": progress_update.id,
                "progress_percentage": progress_percentage,
                "hours_worked": str(hours_worked),
                "has_image": bool(progress_update.image),
            },
            level="INFO",
        )

        if progress_percentage == 100:
            cls._ensure_required_checklist_complete(task)

            return cls.complete_task(
                task=task,
                employee=employee,
                note=note or "Task reached 100% progress.",
            )

        return task

    # =====================================================
    # PAUSE TASK
    # =====================================================

    @classmethod
    @transaction.atomic
    def pause_task(
        cls,
        task,
        employee=None,
        note="",
    ):
        if task.status != "IN_PROGRESS":
            raise ValidationError(
                "Only tasks in progress can be paused."
            )

        previous_status = task.status
        task.status = "PAUSED"

        task.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        cls._log(
            task=task,
            action="PAUSED",
            employee=employee,
            previous_status=previous_status,
            new_status=task.status,
            note=note,
        )

        cls._timeline(
            task=task,
            action=f"Task paused: {task.name}",
            performed_by=employee,
            note=note,
        )

        cls._dispatch(
            event_code="FURNITURE_TASK_PAUSED",
            task=task,
            actor=cls._actor_from_employee(employee),
            title="Production Task Paused",
            message=f"Task '{task.name}' has been paused.",
            metadata={
                "task_id": task.id,
                "production_job_id": task.production_job_id,
                "note": note,
            },
            level="WARNING",
        )

        return task

    # =====================================================
    # BLOCK TASK
    # =====================================================

    @classmethod
    @transaction.atomic
    def block_task(
        cls,
        task,
        employee=None,
        reason="",
    ):
        if task.status in {
            "COMPLETED",
            "CANCELLED",
        }:
            raise ValidationError(
                "Completed or cancelled tasks cannot be blocked."
            )

        if not reason:
            raise ValidationError(
                "A reason is required when blocking a task."
            )

        previous_status = task.status
        task.status = "BLOCKED"

        task.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        cls._log(
            task=task,
            action="BLOCKED",
            employee=employee,
            previous_status=previous_status,
            new_status=task.status,
            note=reason,
        )

        cls._timeline(
            task=task,
            action=f"Task blocked: {task.name}",
            performed_by=employee,
            note=reason,
        )

        cls._dispatch(
            event_code="FURNITURE_TASK_BLOCKED",
            task=task,
            actor=cls._actor_from_employee(employee),
            title="Production Task Blocked",
            message=f"Task '{task.name}' has been blocked.",
            metadata={
                "task_id": task.id,
                "production_job_id": task.production_job_id,
                "reason": reason,
            },
            level="DANGER",
        )

        return task

    # =====================================================
    # COMPLETE TASK
    # =====================================================

    @classmethod
    @transaction.atomic
    def complete_task(
        cls,
        task,
        employee=None,
        hours_worked=Decimal("0.00"),
        note="",
    ):
        if task.status == "COMPLETED":
            raise ValidationError(
                "This task is already completed."
            )

        if task.status == "CANCELLED":
            raise ValidationError(
                "Cancelled tasks cannot be completed."
            )

        cls._ensure_required_checklist_complete(task)

        if hours_worked is None:
            hours_worked = Decimal("0.00")

        if not isinstance(hours_worked, Decimal):
            hours_worked = Decimal(str(hours_worked))

        if hours_worked < 0:
            raise ValidationError(
                "Hours worked cannot be negative."
            )

        if progress_percentage == 100:
            cls._ensure_required_checklist_complete(task)

        previous_status = task.status
        task.status = "COMPLETED"
        task.progress_percentage = 100
        task.completed_at = timezone.now()
        task.actual_hours += hours_worked

        if not task.started_at:
            task.started_at = timezone.now()

        task.save(
            update_fields=[
                "status",
                "progress_percentage",
                "started_at",
                "completed_at",
                "actual_hours",
                "updated_at",
            ]
        )

        ProductionTaskAssignment.objects.filter(
            task=task,
            is_active=True,
        ).update(
            is_active=False,
            released_at=timezone.now(),
        )

        cls._log(
            task=task,
            action="COMPLETED",
            employee=employee,
            previous_status=previous_status,
            new_status=task.status,
            hours_worked=hours_worked,
            progress_percentage=100,
            note=note or "Task completed.",
        )

        cls._timeline(
            task=task,
            action=f"Task completed: {task.name}",
            performed_by=employee,
            note=note,
        )

        cls._dispatch(
            event_code="FURNITURE_TASK_COMPLETED",
            task=task,
            actor=cls._actor_from_employee(employee),
            title="Production Task Completed",
            message=f"Task '{task.name}' has been completed.",
            metadata={
                "task_id": task.id,
                "production_job_id": task.production_job_id,
                "actual_hours": str(task.actual_hours),
            },
            level="SUCCESS",
        )

        cls._update_job_progress(task.production_job)

        return task

    # =====================================================
    # CANCEL TASK
    # =====================================================

    @classmethod
    @transaction.atomic
    def cancel_task(
        cls,
        task,
        employee=None,
        reason="",
    ):
        if task.status == "COMPLETED":
            raise ValidationError(
                "Completed tasks cannot be cancelled."
            )

        if task.status == "CANCELLED":
            raise ValidationError(
                "This task is already cancelled."
            )

        previous_status = task.status
        task.status = "CANCELLED"

        task.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        ProductionTaskAssignment.objects.filter(
            task=task,
            is_active=True,
        ).update(
            is_active=False,
            released_at=timezone.now(),
        )

        cls._log(
            task=task,
            action="CANCELLED",
            employee=employee,
            previous_status=previous_status,
            new_status=task.status,
            note=reason,
        )

        cls._timeline(
            task=task,
            action=f"Task cancelled: {task.name}",
            performed_by=employee,
            note=reason,
        )

        cls._dispatch(
            event_code="FURNITURE_TASK_CANCELLED",
            task=task,
            actor=cls._actor_from_employee(employee),
            title="Production Task Cancelled",
            message=f"Task '{task.name}' has been cancelled.",
            metadata={
                "task_id": task.id,
                "production_job_id": task.production_job_id,
                "reason": reason,
            },
            level="WARNING",
        )

        cls._update_job_progress(task.production_job)

        return task

    # =====================================================
    # JOB PROGRESS
    # =====================================================

    @staticmethod
    def _update_job_progress(production_job):
        tasks = production_job.tasks.exclude(
            status="CANCELLED"
        )

        total_tasks = tasks.count()

        if total_tasks == 0:
            return 0

        total_progress = sum(
            task.progress_percentage
            for task in tasks
        )

        return round(total_progress / total_tasks, 2)

    @classmethod
    def job_progress(cls, production_job):
        return cls._update_job_progress(production_job)