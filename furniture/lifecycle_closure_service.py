from django.core.exceptions import ValidationError
from django.db import transaction

from core.event_engine import EventEngine

from .lifecycle_evidence import ProductionJobLifecycleEvidence
from .lifecycle_guards import ProductionJobTransitionGuard
from .models import ProductionTimeline


class ProductionJobClosureService:
    @staticmethod
    def _actor_user(performed_by):
        return getattr(performed_by, "user", None)

    @staticmethod
    def _timeline(*, job, action, from_status, to_status, performed_by=None, note=""):
        return ProductionTimeline.objects.create(
            production_job=job,
            action=action,
            from_status=from_status,
            to_status=to_status,
            performed_by=performed_by,
            note=note or "",
        )

    @classmethod
    @transaction.atomic
    def confirm_delivery_from_order(cls, job, *, performed_by=None, note=""):
        job = job.__class__.objects.select_for_update().get(pk=job.pk)
        ProductionJobTransitionGuard.assert_can_mark_delivered(job)

        old_status = job.status
        job.status = "DELIVERED"
        job.save(update_fields=["status"])

        cls._timeline(
            job=job,
            action="Order delivery confirmed",
            from_status=old_status,
            to_status="DELIVERED",
            performed_by=performed_by,
            note=note or "Delivery completion mirrored from the Order Engine.",
        )

        EventEngine.dispatch(
            event_code="FURNITURE_DELIVERY_CONFIRMED",
            actor=cls._actor_user(performed_by),
            obj=job,
            title="Furniture Delivery Confirmed",
            message=f"Production job #{job.pk} delivery was confirmed from the Order Engine.",
            level="SUCCESS",
            metadata={"production_job_id": job.pk, "order_id": job.order_id},
            notify_groups=["Furniture Manager", "Finance Manager"],
            notify_owner=True,
        )
        return job

    @classmethod
    @transaction.atomic
    def move_to_finance(cls, job, *, performed_by=None, note=""):
        job = job.__class__.objects.select_for_update().get(pk=job.pk)

        if job.status != "DELIVERED":
            raise ValidationError(
                "Only a delivered Production Job can move to Finance / Profit review."
            )

        evidence = ProductionJobLifecycleEvidence.build(job)
        if evidence["order"]["exists"] and not evidence["delivery"]["complete"]:
            raise ValidationError(
                "Order delivery must be complete before Finance / Profit review."
            )

        old_status = job.status
        job.status = "FINANCE"
        job.save(update_fields=["status"])

        cls._timeline(
            job=job,
            action="Finance and profit review started",
            from_status=old_status,
            to_status="FINANCE",
            performed_by=performed_by,
            note=note,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_FINANCE_REVIEW_STARTED",
            actor=cls._actor_user(performed_by),
            obj=job,
            title="Furniture Finance Review Started",
            message=f"Production job #{job.pk} entered final Finance / Profit review.",
            level="INFO",
            metadata={"production_job_id": job.pk, "order_id": job.order_id},
            notify_groups=["Furniture Manager", "Accountant", "Finance Manager"],
        )
        return job

    @classmethod
    @transaction.atomic
    def close_job(cls, job, *, performed_by=None, note=""):
        job = job.__class__.objects.select_for_update().get(pk=job.pk)
        ProductionJobTransitionGuard.assert_can_close(job)

        old_status = job.status
        job.status = "CLOSED"
        job.save(update_fields=["status"])

        cls._timeline(
            job=job,
            action="Production lifecycle closed",
            from_status=old_status,
            to_status="CLOSED",
            performed_by=performed_by,
            note=note or "Delivery and financial obligations completed.",
        )

        EventEngine.dispatch(
            event_code="FURNITURE_PRODUCTION_CLOSED",
            actor=cls._actor_user(performed_by),
            obj=job,
            title="Furniture Production Job Closed",
            message=f"Production job #{job.pk} lifecycle is fully closed.",
            level="SUCCESS",
            metadata={"production_job_id": job.pk, "order_id": job.order_id},
            notify_groups=["Furniture Manager", "Accountant", "Finance Manager"],
            notify_owner=True,
        )
        return job
