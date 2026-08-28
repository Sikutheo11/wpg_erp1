from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.decorators import login_required
from core.event_engine import EventEngine
from inventory.services import StockService
from furniture.lifecycle_guards import ProductionJobTransitionGuard
from furniture.models import (
    ProductionJob,
    ProductionOutput,
    ProductionTimeline,
)


class ProductionService:
    """
    Furniture production business logic.

    Handles:
    - creating production jobs
    - assigning workers
    - starting production
    - completing production
    - recording outputs
    - timeline events
    """

    @staticmethod
    def add_timeline(
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
            from_status=from_status or "",
            to_status=to_status or "",
            performed_by=performed_by,
            note=note or "",
        )

    @staticmethod
    @transaction.atomic
    def create_job(
        order=None,
        product=None,
        job_type="RESTOCK",
        quantity_to_produce=1,
        assigned_to=None,
        created_by=None,
        description="",
        expected_end_date=None,
    ):
        """
        Create a production job.

        Rules:
        - A production job must have an order or a product.
        - One customer order can have only one production job.
        - CUSTOMER_CUSTOM and BACKORDER require an order.
        - RESTOCK and NEW_PRODUCT require a product.
        """

        allowed_job_types = {
            "RESTOCK",
            "CUSTOMER_CUSTOM",
            "NEW_PRODUCT",
            "BACKORDER",
        }

        if job_type not in allowed_job_types:
            raise ValidationError(
                "Invalid production job type."
            )

        if not order and not product:
            raise ValidationError(
                "Production job must have either an order or a product."
            )

        if quantity_to_produce is None or quantity_to_produce < 1:
            raise ValidationError(
                "Quantity to produce must be at least one."
            )

        # One order can create only one production job.
        if order:
            if not getattr(order, "is_production_authorized", False):
                raise ValidationError(
                    "This order is not ready for production. Complete and approve its quotation or costing first."
                )
            existing_job = (
                ProductionJob.objects
                .filter(order=order)
                .first()
            )

            if existing_job:
                raise ValidationError(
                    (
                        "This customer order already has "
                        f"Production Job #{existing_job.pk}."
                    )
                )

        # Customer-based job types require an order.
        if job_type in {
            "CUSTOMER_CUSTOM",
            "BACKORDER",
        } and not order:
            raise ValidationError(
                (
                    f"{job_type} production jobs require "
                    "a customer order."
                )
            )

        # Product-based job types require a product.
        if job_type in {
            "RESTOCK",
            "NEW_PRODUCT",
        } and not product:
            raise ValidationError(
                (
                    f"{job_type} production jobs require "
                    "a product."
                )
            )

        # Use the product linked to the order when possible.
        if product is None and order is not None:
            product = getattr(
                order,
                "product",
                None,
            )

        job = ProductionJob.objects.create(
            order=order,
            product=product,
            job_type=job_type,
            quantity_to_produce=quantity_to_produce,
            assigned_to=assigned_to,
            created_by=created_by,
            description=description or "",
            expected_end_date=expected_end_date,
            status="QUOTATION",
        )

        ProductionService.add_timeline(
            production_job=job,
            action="Production job created",
            from_status="",
            to_status="QUOTATION",
            performed_by=created_by,
            note=(
                f"{job.get_job_type_display()} created "
                f"for quantity {job.quantity_to_produce}."
            ),
        )

        EventEngine.dispatch(
            event_code="FURNITURE_PRODUCTION_JOB_CREATED",
            actor=getattr(
                created_by,
                "user",
                None,
            ),
            obj=job,
            title="Production Job Created",
            message=(
                f"Production job #{job.pk} "
                "has been created."
            ),
            level="INFO",
            metadata={
                "production_job_id": job.pk,
                "order_id": job.order_id,
                "product_id": job.product_id,
                "job_type": job.job_type,
                "quantity_to_produce": (
                    job.quantity_to_produce
                ),
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
            notify_owner=True,
        )

        return job

    @staticmethod
    @transaction.atomic
    def assign_worker(production_job, employee, assigned_by=None):
        old_assignee = production_job.assigned_to

        production_job.assigned_to = employee
        production_job.save()

        ProductionService.add_timeline(
            production_job=production_job,
            action="Worker assigned",
            performed_by=assigned_by,
            note=f"Assigned to {employee}",
        )

        EventEngine.dispatch(
            event_code="FURNITURE_WORKER_ASSIGNED",
            actor=getattr(assigned_by, "user", None),
            obj=production_job,
            title="Worker Assigned",
            message=f"Production job #{production_job.id} assigned to {employee}.",
            level="INFO",
            metadata={
                "production_job_id": production_job.id,
                "old_assignee": str(old_assignee) if old_assignee else "",
                "new_assignee": str(employee),
            },
            notify_users=[
                getattr(employee, "user", None),
            ],
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
        )

        return production_job

    @staticmethod
    @transaction.atomic
    def confirm_order(production_job, performed_by=None, note=""):
        if production_job.status != "APPROVED":
            raise ValidationError(
                "Only approved production jobs can be confirmed."
            )

        old_status = production_job.status
        production_job.status = "ORDER_CONFIRMED"
        production_job.save()

        ProductionService.add_timeline(
            production_job=production_job,
            action="Order confirmed",
            from_status=old_status,
            to_status="ORDER_CONFIRMED",
            performed_by=performed_by,
            note=note,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_ORDER_CONFIRMED",
            actor=getattr(performed_by, "user", None),
            obj=production_job,
            title="Order Confirmed",
            message=f"Production job #{production_job.id} order confirmed.",
            level="SUCCESS",
            metadata={
                "production_job_id": production_job.id,
                "from_status": old_status,
                "to_status": "ORDER_CONFIRMED",
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
                "Store Keeper",
            ],
        )

        return production_job

    @login_required
    def add_material(request, pk):
        production_job = get_object_or_404(
            ProductionJob,
            pk=pk,
        )

        if request.method == "POST":
            form = ProductionMaterialForm(
                request.POST
            )

            if form.is_valid():
                try:
                    material = ProductionService.add_material(
                        production_job=production_job,
                        raw_material=form.cleaned_data[
                            "raw_material"
                        ],
                        quantity_used=form.cleaned_data[
                            "quantity_used"
                        ],
                    )

                except ValidationError as error:
                    form.add_error(
                        None,
                        _validation_message(error),
                    )

                else:
                    messages.success(
                        request,
                        (
                            f"{material.raw_material} added "
                            "successfully."
                        ),
                    )

                    return redirect(
                        "furniture:production_job_detail",
                        pk=production_job.pk,
                    )

        else:
            form = ProductionMaterialForm()

        return render(
            request,
            "furniture/material_form.html",
            {
                "form": form,
                "production_job": production_job,
                "page_title": "Record Material Consumption",
            },
        )

    @staticmethod
    @transaction.atomic
    def start_production(production_job, performed_by=None, note=""):
        ProductionJobTransitionGuard.assert_can_start_production(
            production_job
        )
        if production_job.status not in [
            "ORDER_CONFIRMED",
            "MATERIAL_RESERVED",
        ]:
            raise ValidationError(
                "Production can start only after order confirmation or material reservation."
            )

        old_status = production_job.status
        production_job.status = "IN_PRODUCTION"
        production_job.save()

        ProductionService.add_timeline(
            production_job=production_job,
            action="Production started",
            from_status=old_status,
            to_status="IN_PRODUCTION",
            performed_by=performed_by,
            note=note,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_PRODUCTION_STARTED",
            actor=getattr(performed_by, "user", None),
            obj=production_job,
            title="Production Started",
            message=f"Production job #{production_job.id} has started.",
            level="INFO",
            metadata={
                "production_job_id": production_job.id,
                "from_status": old_status,
                "to_status": "IN_PRODUCTION",
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
            notify_owner=True,
        )

        return production_job

    @staticmethod
    @transaction.atomic
    def move_to_quality_check(production_job, performed_by=None, note=""):
        if production_job.status != "IN_PRODUCTION":
            raise ValidationError(
                "Only jobs in production can move to quality check."
            )

        old_status = production_job.status
        production_job.status = "QUALITY_CHECK"
        production_job.save()

        ProductionService.add_timeline(
            production_job=production_job,
            action="Moved to quality check",
            from_status=old_status,
            to_status="QUALITY_CHECK",
            performed_by=performed_by,
            note=note,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_QUALITY_CHECK_REQUIRED",
            actor=getattr(performed_by, "user", None),
            obj=production_job,
            title="Quality Check Required",
            message=f"Production job #{production_job.id} is ready for quality inspection.",
            level="INFO",
            metadata={
                "production_job_id": production_job.id,
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
        )

        return production_job

    @staticmethod
    @transaction.atomic
    def mark_finished_goods(production_job, performed_by=None, note=""):
        ProductionJobTransitionGuard.assert_legacy_finished_goods_transition_disabled(
            production_job
        )
        if production_job.status != "QUALITY_CHECK":
            raise ValidationError(
                "Only jobs in quality check can be marked as finished goods."
            )

        old_status = production_job.status
        production_job.status = "FINISHED_GOODS"
        production_job.save()

        ProductionService.add_timeline(
            production_job=production_job,
            action="Marked as finished goods",
            from_status=old_status,
            to_status="FINISHED_GOODS",
            performed_by=performed_by,
            note=note,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_FINISHED_GOODS",
            actor=getattr(performed_by, "user", None),
            obj=production_job,
            title="Finished Goods",
            message=f"Production job #{production_job.id} is now finished goods.",
            level="SUCCESS",
            metadata={
                "production_job_id": production_job.id,
            },
            notify_groups=[
                "Furniture Manager",
                "Store Keeper",
            ],
        )

        return production_job

    @staticmethod
    @transaction.atomic
    def record_output(
        production_job,
        product,
        quantity_produced,
        warehouse=None,
        produced_by=None,
        actor=None,
        image=None,
    ):
        # Compatibility wrapper. Never receive finished stock here.
        from furniture.lifecycle_service import FurnitureProductionLifecycleService

        return FurnitureProductionLifecycleService.record_output(
            production_job=production_job,
            product=product,
            quantity_produced=quantity_produced,
            produced_by=produced_by,
            image=image,
        )

    @staticmethod
    @transaction.atomic
    def deliver(production_job, performed_by=None, note=""):
        ProductionJobTransitionGuard.assert_can_mark_delivered(
            production_job
        )
        if production_job.status != "FINISHED_GOODS":
            raise ValidationError(
                "Only finished goods can be delivered."
            )

        old_status = production_job.status
        production_job.status = "DELIVERED"
        production_job.save()

        ProductionService.add_timeline(
            production_job=production_job,
            action="Delivered",
            from_status=old_status,
            to_status="DELIVERED",
            performed_by=performed_by,
            note=note,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_DELIVERED",
            actor=getattr(performed_by, "user", None),
            obj=production_job,
            title="Furniture Delivered",
            message=f"Production job #{production_job.id} has been delivered.",
            level="SUCCESS",
            metadata={
                "production_job_id": production_job.id,
            },
            notify_groups=[
                "Furniture Manager",
                "Sales Officer",
            ],
            notify_owner=True,
        )

        return production_job

    @staticmethod
    @transaction.atomic
    def cancel(production_job, performed_by=None, note=""):
        if production_job.status in [
            "DELIVERED",
            "CANCELLED",
        ]:
            raise ValidationError(
                "Delivered or cancelled jobs cannot be cancelled again."
            )

        old_status = production_job.status
        production_job.status = "CANCELLED"
        production_job.save()

        ProductionService.add_timeline(
            production_job=production_job,
            action="Production job cancelled",
            from_status=old_status,
            to_status="CANCELLED",
            performed_by=performed_by,
            note=note,
        )

        EventEngine.dispatch(
            event_code="FURNITURE_PRODUCTION_CANCELLED",
            actor=getattr(performed_by, "user", None),
            obj=production_job,
            title="Production Cancelled",
            message=f"Production job #{production_job.id} has been cancelled.",
            level="WARNING",
            metadata={
                "production_job_id": production_job.id,
                "from_status": old_status,
                "to_status": "CANCELLED",
                "note": note,
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
            ],
        )

        return production_job

class ProductionCostingMaterialGuard:
    @staticmethod
    def approved_plan_for_job(production_job):
        if not production_job.order_id:
            raise ValidationError("This production job has no linked Order.")
        from furniture.planner_models import ProductionPlan
        plan = (
            ProductionPlan.objects.filter(order_id=production_job.order_id, status="APPROVED")
            .prefetch_related("materials__raw_material")
            .order_by("-updated_at")
            .first()
        )
        if not plan:
            raise ValidationError(
                "No approved Production Costing exists for this Order. "
                "Approve technical costing before requesting or consuming materials."
            )
        return plan

    @staticmethod
    def assert_material_in_approved_costing(production_job, raw_material, quantity):
        from django.db.models import Sum
        from furniture.models import ProductionMaterial
        plan = ProductionCostingMaterialGuard.approved_plan_for_job(production_job)
        line = plan.materials.filter(raw_material=raw_material).first()
        if not line:
            raise ValidationError(
                f"{raw_material} was not included in the approved Production Costing for this Order. "
                "Update and re-approve the Production Plan before requesting it."
            )
        used = (
            ProductionMaterial.objects.filter(
                production_job=production_job, raw_material=raw_material
            ).aggregate(total=Sum("quantity_used"))["total"] or 0
        )
        if used + quantity > line.estimated_quantity:
            raise ValidationError(
                f"Quantity exceeds approved costing. Approved: {line.estimated_quantity}; "
                f"already recorded: {used}; requested: {quantity}."
            )
        return line
