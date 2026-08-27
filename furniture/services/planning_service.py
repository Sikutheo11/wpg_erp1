from datetime import timedelta

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone


class PlanningService:

    @classmethod
    @transaction.atomic
    def schedule_job(
        cls,
        production_job,
        start_datetime=None,
    ):

        if start_datetime is None:
            start_datetime = timezone.now()

        if production_job.status in {"FINISHED_GOODS", "DELIVERED", "CANCELLED"}:
            raise ValidationError(
                "Finished, delivered or cancelled jobs cannot be scheduled."
            )

        current_start = start_datetime

        tasks = (
            production_job.tasks
            .filter(status__in={"PENDING", "READY"})
            .order_by(
                "sequence",
                "id",
            )
        )

        if not tasks.exists():
            raise ValidationError(
                "Add at least one pending or ready task before generating a schedule."
            )

        zero_hour_tasks = list(
            tasks.filter(planned_hours__lte=0).values_list("name", flat=True)
        )
        if zero_hour_tasks:
            raise ValidationError(
                "Set planned hours above zero for: " + ", ".join(zero_hour_tasks)
            )

        for task in tasks:

            duration = float(task.planned_hours or 0)

            task.planned_start = current_start

            task.planned_end = (
                current_start
                + timedelta(hours=duration)
            )

            task.save(
                update_fields=[
                    "planned_start",
                    "planned_end",
                ]
            )

            current_start = task.planned_end

        return production_job
