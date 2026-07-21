from datetime import timedelta

from django.db import transaction
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

        current_start = start_datetime

        tasks = (
            production_job.tasks
            .order_by(
                "sequence",
                "id",
            )
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