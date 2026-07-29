from django.core.exceptions import ValidationError
from django.db import transaction

from inventory.models import StockMovement
from inventory.services.stock_service import StockService

from ..models import EggProduction, FeedingRecord, IncubationBatch


class AgricultureInventoryIntegrationService:
    """
    Posts Agriculture outputs and consumption through Inventory StockService.

    The Agriculture record is locked before checking or creating a movement.
    This makes retries idempotent and prevents duplicate stock postings.
    """

    BUSINESS_UNIT = "AGRICULTURE"

    @staticmethod
    def _saved(record, expected_model):
        if record is None or not isinstance(record, expected_model):
            raise ValidationError(
                f"A saved {expected_model.__name__} record is required."
            )
        if not record.pk:
            raise ValidationError(
                f"The {expected_model.__name__} record must be saved first."
            )

    @staticmethod
    def _reference_no(record):
        operation = getattr(record, "operation", None)
        if operation is not None:
            return operation.code
        return f"AGRICULTURE-{record._meta.model_name.upper()}-{record.pk}"

    @staticmethod
    def _find_existing(*, reference_type, reference_id):
        return (
            StockMovement.objects.filter(
                reference_type=reference_type,
                reference_id=str(reference_id),
                status="POSTED",
            )
            .order_by("pk")
            .first()
        )

    @classmethod
    def _link(cls, *, record, movement):
        if record.stock_movement_id:
            if record.stock_movement_id != movement.pk:
                raise ValidationError(
                    "This Agriculture record is linked to another stock movement."
                )
            return record

        record.stock_movement = movement
        record.save(update_fields=["stock_movement", "updated_at"])
        return record

    @classmethod
    @transaction.atomic
    def receive_egg_output(cls, *, egg_record, actor=None):
        cls._saved(egg_record, EggProduction)
        record = EggProduction.objects.select_for_update().get(
            pk=egg_record.pk
        )

        if record.stock_movement_id:
            return record.stock_movement

        if not record.inventory_product_id or not record.warehouse_id:
            return None

        if record.saleable_eggs <= 0:
            return None

        movement = cls._find_existing(
            reference_type="EGG_COLLECTION",
            reference_id=record.pk,
        )
        if movement is None:
            movement = StockService.receive_stock(
                product=record.inventory_product,
                warehouse=record.warehouse,
                quantity=record.saleable_eggs,
                business_unit=cls.BUSINESS_UNIT,
                reference_type="EGG_COLLECTION",
                reference_id=str(record.pk),
                reference_no=cls._reference_no(record),
                notes=(
                    f"Saleable egg output from flock "
                    f"{record.flock.code} on {record.record_date}."
                ),
                actor=actor,
                movement_type="IN",
            )

        cls._link(record=record, movement=movement)
        return movement

    @classmethod
    @transaction.atomic
    def issue_feed(cls, *, feeding_record, actor=None):
        cls._saved(feeding_record, FeedingRecord)
        record = FeedingRecord.objects.select_for_update().get(
            pk=feeding_record.pk
        )

        if record.stock_movement_id:
            return record.stock_movement

        movement = cls._find_existing(
            reference_type="FEED_CONSUMPTION",
            reference_id=record.pk,
        )
        if movement is None:
            movement = StockService.issue_stock(
                product=record.feed_product,
                warehouse=record.warehouse,
                quantity=record.quantity_kg,
                unit_cost=record.unit_cost,
                business_unit=cls.BUSINESS_UNIT,
                reference_type="FEED_CONSUMPTION",
                reference_id=str(record.pk),
                reference_no=cls._reference_no(record),
                notes=(
                    f"Feed consumed by flock {record.flock.code} "
                    f"on {record.record_date}."
                ),
                actor=actor,
                movement_type="OUT",
                include_reserved_stock=False,
            )

        cls._link(record=record, movement=movement)
        return movement

    @classmethod
    @transaction.atomic
    def receive_chick_output(cls, *, batch, actor=None):
        cls._saved(batch, IncubationBatch)
        locked = IncubationBatch.objects.select_for_update().get(pk=batch.pk)

        if locked.stock_movement_id:
            return locked.stock_movement

        if not locked.chick_product_id or not locked.output_warehouse_id:
            return None

        if locked.chicks_hatched <= 0:
            return None

        movement = cls._find_existing(
            reference_type="INCUBATION",
            reference_id=locked.pk,
        )
        if movement is None:
            movement = StockService.receive_stock(
                product=locked.chick_product,
                warehouse=locked.output_warehouse,
                quantity=locked.chicks_hatched,
                business_unit=cls.BUSINESS_UNIT,
                reference_type="INCUBATION",
                reference_id=str(locked.pk),
                reference_no=cls._reference_no(locked),
                notes=(
                    f"Chick output from incubation batch {locked.code} "
                    f"completed on {locked.actual_hatch_date}."
                ),
                actor=actor,
                movement_type="IN",
            )

        cls._link(record=locked, movement=movement)
        return movement
