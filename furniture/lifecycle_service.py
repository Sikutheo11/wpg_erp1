from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from inventory.models import StockMovement
from .models import ProductionOutput, QualityInspection

class FurnitureProductionLifecycleService:
    @classmethod
    @transaction.atomic
    def record_output(cls, *, production_job, product, quantity_produced, produced_by=None, image=None):
        if production_job.status not in {"IN_PRODUCTION", "QUALITY_CHECK"}:
            raise ValidationError("Output can be recorded only during production or quality check.")
        if product is None:
            raise ValidationError("Production job must have a product.")
        qty = int(quantity_produced or 0)
        produced = sum(int(x.quantity_produced or 0) for x in production_job.outputs.all())
        remaining = int(production_job.quantity_to_produce or 0) - produced
        if qty <= 0 or qty > remaining:
            raise ValidationError(f"Produced quantity must be between 1 and {max(remaining, 0)}.")
        output = ProductionOutput.objects.create(production_job=production_job, product=product, quantity_produced=qty, produced_by=produced_by, image=image)
        if produced + qty >= int(production_job.quantity_to_produce or 0):
            production_job.status = "QUALITY_CHECK"
            production_job.save(update_fields=["status"])
        return output

    @classmethod
    @transaction.atomic
    def mark_ready_for_finished_goods(cls, inspection):
        inspection = QualityInspection.objects.select_related("production_job").get(pk=inspection.pk)
        job = inspection.production_job
        if inspection.inspection_type != "FINAL" or inspection.result != "PASSED":
            raise ValidationError("A PASSED final inspection is required.")
        if not inspection.approved_at or not inspection.approved_by_id:
            raise ValidationError("Final inspection must be formally approved.")
        if job.quality_defects.exclude(status__in={"RESOLVED", "ACCEPTED", "SCRAPPED"}).exists():
            raise ValidationError("Resolve all quality defects before release.")
        if job.rework_orders.exclude(status__in={"VERIFIED", "CANCELLED"}).exists():
            raise ValidationError("Verify all rework before release.")
        output_qty = sum(int(x.quantity_produced or 0) for x in job.outputs.all())
        if output_qty <= 0 or int(inspection.quantity_passed or 0) < output_qty:
            raise ValidationError("Approved passed quantity must cover recorded output.")
        job.status = "READY_FOR_FINISHED_GOODS"
        job.save(update_fields=["status"])
        return job

    @classmethod
    @transaction.atomic
    def release_to_finished_goods(cls, *, production_job, warehouse, actor):
        # Lock the ProductionJob itself without joining nullable relations.
        # PostgreSQL does not allow FOR UPDATE on the nullable side of an
        # outer join.
        job = (
            production_job.__class__.objects
            .select_for_update()
            .get(pk=production_job.pk)
        )

        # Resolve Product separately after the job row has been locked.
        product = job.product
        if job.status != "READY_FOR_FINISHED_GOODS":
            raise ValidationError("Job must be READY FOR FINISHED GOODS.")
        if not warehouse or warehouse.warehouse_type != "FINISHED_GOODS" or warehouse.business_unit != "FURNITURE" or not warehouse.is_active:
            raise ValidationError("Select an active Furniture FINISHED_GOODS warehouse.")
        inspection = QualityInspection.objects.filter(production_job=job, inspection_type="FINAL", result="PASSED", approved_at__isnull=False, approved_by__isnull=False).order_by("-approved_at", "-pk").first()
        if not inspection:
            raise ValidationError("Approved PASSED final inspection is required.")
        outputs = job.outputs.select_for_update().filter(inventory_movement__isnull=True)
        if not outputs.exists():
            raise ValidationError("No unreleased output remains.")
        released = []
        for output in outputs:
            movement = StockMovement.objects.create(product=output.product, warehouse=warehouse, movement_type="IN", status="POSTED", quantity=output.quantity_produced, unit_cost=Decimal(str(output.cost_per_unit or 0)), business_unit="FURNITURE", reference_type="PRODUCTION_JOB", reference_id=str(job.pk), reference_no=f"PRODUCTION-JOB-{job.pk}-OUTPUT-{output.pk}", notes=f"Quality-approved furniture; final inspection #{inspection.pk}.", created_by=actor)
            output.inventory_movement = movement
            output.inventory_released_at = timezone.now()
            output.inventory_released_by = actor
            output.save(update_fields=["inventory_movement", "inventory_released_at", "inventory_released_by"])
            released.append(output)
        if job.product and not job.product.track_inventory:
            job.product.track_inventory = True
            job.product.save(update_fields=["track_inventory", "updated_at"])
        job.status = "FINISHED_GOODS"
        job.save(update_fields=["status"])
        return released
