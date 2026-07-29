from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from core.event_engine import EventEngine
from ..models import (
    AgricultureOperation,
    DailyFlockRecord,
    EggProduction,
    FeedingRecord,
    HealthRecord,
    IncubationBatch,
    MortalityRecord,
    PoultryFlock,
    PoultryHouse,
)


class PoultryService:
    """
    Application service for poultry production records.

    Agriculture owns biological and production records. Inventory and Finance
    consume the emitted Core events and attach their posting references without
    Agriculture duplicating stock or accounting logic.
    """

    BUSINESS_UNIT = AgricultureOperation.BUSINESS_UNIT

    ACTIVE_FLOCK_STATUSES = {"ACTIVE", "QUARANTINED"}
    ACTIVE_OPERATION_STATUSES = {"APPROVED", "ACTIVE", "ON_HOLD"}

    @staticmethod
    def _authenticated_user(user):
        if user is not None and getattr(user, "is_authenticated", False):
            return user
        return None

    @staticmethod
    def _as_decimal(value, field_name, *, minimum=Decimal("0.00")):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValidationError({field_name: "Enter a valid number."}) from exc

        if result < minimum:
            raise ValidationError(
                {field_name: f"This value must be at least {minimum}."}
            )
        return result

    @classmethod
    def _dispatch(
        cls,
        event_code,
        obj,
        *,
        actor=None,
        operation=None,
        flock=None,
        **metadata,
    ):
        operation = operation or getattr(obj, "operation", None)
        flock = flock or getattr(obj, "flock", None)

        EventEngine.dispatch(
            event_code=event_code,
            actor=cls._authenticated_user(actor),
            obj=obj,
            title=event_code.replace("_", " ").title(),
            message=f"{event_code} recorded in Agriculture.",
            level="INFO",
            metadata={
                "business_unit": cls.BUSINESS_UNIT,
                "record_id": obj.pk,
                "operation_id": getattr(operation, "pk", None),
                "operation_code": getattr(operation, "code", None),
                "flock_id": getattr(flock, "pk", None),
                "flock_code": getattr(flock, "code", None),
                **metadata,
            },
        )

    @staticmethod
    def _generate_code(prefix, model):
        date_prefix = timezone.localdate().strftime(f"{prefix}-%Y%m%d")

        while True:
            code = f"{date_prefix}-{uuid4().hex[:8].upper()}"
            if not model.objects.filter(code=code).exists():
                return code

    @classmethod
    def _lock_flock(cls, flock):
        if flock is None or not getattr(flock, "pk", None):
            raise ValidationError({"flock": "A saved poultry flock is required."})

        # Lock only the flock row. source_operation and livestock_product are
        # nullable; select_related() would create outer joins that PostgreSQL
        # cannot lock with FOR UPDATE.
        return PoultryFlock.objects.select_for_update().get(pk=flock.pk)

    @classmethod
    def _validate_flock_is_operational(cls, flock):
        if flock.status not in cls.ACTIVE_FLOCK_STATUSES:
            raise ValidationError(
                {
                    "flock": (
                        f"Flock {flock.code} must be ACTIVE or QUARANTINED "
                        "for this operation."
                    )
                }
            )

    @classmethod
    def _validate_operation(cls, operation, *, flock=None):
        if operation is None:
            return

        if not getattr(operation, "pk", None):
            raise ValidationError(
                {"operation": "A saved agriculture operation is required."}
            )

        if operation.status not in cls.ACTIVE_OPERATION_STATUSES:
            raise ValidationError(
                {
                    "operation": (
                        f"Operation {operation.code} is not approved or active."
                    )
                }
            )

        if flock is not None and operation.farm_id != flock.farm_id:
            raise ValidationError(
                {"operation": "The operation and flock must use the same farm."}
            )

    @classmethod
    @transaction.atomic
    def create_flock(
        cls,
        *,
        farm,
        house,
        breed,
        purpose,
        source,
        arrival_or_hatch_date,
        initial_quantity,
        actor=None,
        source_operation=None,
        average_unit_cost=Decimal("0.00"),
        livestock_product=None,
        notes="",
        code="",
        activate=True,
    ):
        house = (
            PoultryHouse.objects
            .select_for_update()
            .select_related("farm")
            .get(pk=house.pk)
        )

        if house.farm_id != farm.pk:
            raise ValidationError(
                {"house": "The selected poultry house must belong to the farm."}
            )

        if not farm.is_active:
            raise ValidationError(
                {"farm": "The selected farm is inactive."}
            )

        if not house.is_active:
            raise ValidationError(
                {"house": "The selected poultry house is inactive."}
            )

        if not breed.is_active:
            raise ValidationError(
                {"breed": "The selected poultry breed is inactive."}
            )

        cls._validate_operation(source_operation)

        if (
            source_operation is not None
            and source_operation.farm_id != farm.pk
        ):
            raise ValidationError(
                {
                    "source_operation": (
                        "The source operation must belong to "
                        "the selected farm."
                    )
                }
            )

        initial_quantity = int(initial_quantity)
        if initial_quantity < 1:
            raise ValidationError(
                {"initial_quantity": "Initial quantity must be at least one."}
            )

        occupied = (
            PoultryFlock.objects.select_for_update()
            .filter(
                house=house,
                status__in=cls.ACTIVE_FLOCK_STATUSES,
            )
            .aggregate(total=Sum("current_quantity"))["total"]
            or 0
        )
        if occupied + initial_quantity > house.capacity:
            raise ValidationError(
                {
                    "initial_quantity": (
                        f"House capacity is {house.capacity}; {occupied} birds "
                        "are already assigned."
                    )
                }
            )

        flock = PoultryFlock(
            code=(code or cls._generate_code("FLK", PoultryFlock)).strip(),
            source_operation=source_operation,
            farm=farm,
            house=house,
            breed=breed,
            purpose=purpose,
            source=source,
            status="ACTIVE" if activate else "PLANNED",
            arrival_or_hatch_date=arrival_or_hatch_date,
            initial_quantity=initial_quantity,
            current_quantity=initial_quantity,
            average_unit_cost=cls._as_decimal(
                average_unit_cost,
                "average_unit_cost",
            ),
            livestock_product=livestock_product,
            notes=(notes or "").strip(),
        )
        flock.full_clean()
        flock.save()

        cls._dispatch(
            "AGRICULTURE_FLOCK_CREATED",
            flock,
            actor=actor,
            operation=source_operation,
            flock=flock,
            quantity=flock.initial_quantity,
            product_id=flock.livestock_product_id,
            unit_cost=str(flock.average_unit_cost),
        )
        return flock

    @classmethod
    @transaction.atomic
    def record_daily_flock(
        cls,
        *,
        flock,
        actor=None,
        operation=None,
        record_date=None,
        additions=0,
        transferred_in=0,
        mortality=0,
        culls=0,
        sold=0,
        transferred_out=0,
        average_weight_kg=None,
        notes="",
    ):
        flock = cls._lock_flock(flock)
        cls._validate_flock_is_operational(flock)
        cls._validate_operation(operation, flock=flock)

        record_date = record_date or timezone.localdate()
        if DailyFlockRecord.objects.filter(
            flock=flock,
            record_date=record_date,
        ).exists():
            raise ValidationError(
                {"record_date": "A daily record already exists for this flock."}
            )

        movements = {
            "additions": int(additions),
            "transferred_in": int(transferred_in),
            "mortality": int(mortality),
            "culls": int(culls),
            "sold": int(sold),
            "transferred_out": int(transferred_out),
        }
        if any(value < 0 for value in movements.values()):
            raise ValidationError("Daily flock movements cannot be negative.")

        opening = flock.current_quantity
        closing = (
            opening
            + movements["additions"]
            + movements["transferred_in"]
            - movements["mortality"]
            - movements["culls"]
            - movements["sold"]
            - movements["transferred_out"]
        )
        if closing < 0:
            raise ValidationError(
                "Daily movements cannot exceed the flock's available birds."
            )

        record = DailyFlockRecord(
            operation=operation,
            flock=flock,
            record_date=record_date,
            opening_quantity=opening,
            closing_quantity=closing,
            average_weight_kg=average_weight_kg,
            notes=(notes or "").strip(),
            recorded_by=cls._authenticated_user(actor),
            **movements,
        )
        record.full_clean()
        record.save()

        flock.current_quantity = closing
        flock.save(update_fields=["current_quantity", "updated_at"])

        cls._dispatch(
            "AGRICULTURE_FLOCK_DAILY_RECORDED",
            record,
            actor=actor,
            operation=operation,
            flock=flock,
            opening_quantity=opening,
            closing_quantity=closing,
            **movements,
        )
        return record

    @classmethod
    @transaction.atomic
    def record_egg_production(
        cls,
        *,
        flock,
        eggs_collected,
        saleable_eggs,
        hatching_eggs,
        cracked_eggs,
        rejected_eggs,
        actor=None,
        operation=None,
        record_date=None,
        inventory_product=None,
        warehouse=None,
        notes="",
    ):
        flock = cls._lock_flock(flock)
        cls._validate_flock_is_operational(flock)
        cls._validate_operation(operation, flock=flock)

        record = EggProduction(
            operation=operation,
            flock=flock,
            record_date=record_date or timezone.localdate(),
            eggs_collected=int(eggs_collected),
            saleable_eggs=int(saleable_eggs),
            hatching_eggs=int(hatching_eggs),
            cracked_eggs=int(cracked_eggs),
            dirty_or_rejected_eggs=int(rejected_eggs),
            inventory_product=inventory_product,
            warehouse=warehouse,
            notes=(notes or "").strip(),
            recorded_by=cls._authenticated_user(actor),
        )
        record.full_clean()
        record.save()

        from .inventory_integration_service import (
            AgricultureInventoryIntegrationService,
        )

        stock_movement = (
            AgricultureInventoryIntegrationService.receive_egg_output(
                egg_record=record,
                actor=actor,
            )
        )

        cls._dispatch(
            "AGRICULTURE_EGGS_PRODUCED",
            record,
            actor=actor,
            operation=operation,
            flock=flock,
            eggs_collected=record.eggs_collected,
            saleable_eggs=record.saleable_eggs,
            hatching_eggs=record.hatching_eggs,
            rejected_eggs=(
                record.cracked_eggs + record.dirty_or_rejected_eggs
            ),
            inventory_product_id=record.inventory_product_id,
            warehouse_id=record.warehouse_id,
            inventory_posting_required=bool(
                record.inventory_product_id and record.warehouse_id
            ),
            stock_movement_id=(
                stock_movement.pk if stock_movement is not None else None
            ),
        )
        record.refresh_from_db()
        return record

    @classmethod
    @transaction.atomic
    def record_feeding(
        cls,
        *,
        flock,
        feed_product,
        warehouse,
        quantity_kg,
        actor=None,
        operation=None,
        record_date=None,
        unit_cost=Decimal("0.00"),
        notes="",
    ):
        flock = cls._lock_flock(flock)
        cls._validate_flock_is_operational(flock)
        cls._validate_operation(operation, flock=flock)

        record = FeedingRecord(
            operation=operation,
            flock=flock,
            record_date=record_date or timezone.localdate(),
            feed_product=feed_product,
            warehouse=warehouse,
            quantity_kg=cls._as_decimal(
                quantity_kg,
                "quantity_kg",
                minimum=Decimal("0.001"),
            ),
            unit_cost=cls._as_decimal(unit_cost, "unit_cost"),
            notes=(notes or "").strip(),
            recorded_by=cls._authenticated_user(actor),
        )
        record.full_clean()
        record.save()

        from .inventory_integration_service import (
            AgricultureInventoryIntegrationService,
        )

        stock_movement = AgricultureInventoryIntegrationService.issue_feed(
            feeding_record=record,
            actor=actor,
        )

        cls._dispatch(
            "AGRICULTURE_FEED_CONSUMED",
            record,
            actor=actor,
            operation=operation,
            flock=flock,
            product_id=record.feed_product_id,
            warehouse_id=record.warehouse_id,
            quantity=str(record.quantity_kg),
            unit="KG",
            unit_cost=str(record.unit_cost),
            total_cost=str(record.total_cost),
            inventory_posting_required=True,
            finance_posting_required=record.total_cost > 0,
            stock_movement_id=stock_movement.pk,
        )
        record.refresh_from_db()
        return record

    @classmethod
    @transaction.atomic
    def record_health(
        cls,
        *,
        flock,
        record_type,
        condition_or_vaccine,
        actor=None,
        operation=None,
        record_date=None,
        medicine_product=None,
        dosage="",
        birds_treated=0,
        next_due_date=None,
        veterinarian_or_provider="",
        cost=Decimal("0.00"),
        notes="",
    ):
        flock = cls._lock_flock(flock)
        cls._validate_flock_is_operational(flock)
        cls._validate_operation(operation, flock=flock)

        record = HealthRecord(
            operation=operation,
            flock=flock,
            record_date=record_date or timezone.localdate(),
            record_type=record_type,
            condition_or_vaccine=(condition_or_vaccine or "").strip(),
            medicine_product=medicine_product,
            dosage=(dosage or "").strip(),
            birds_treated=int(birds_treated),
            next_due_date=next_due_date,
            veterinarian_or_provider=(
                veterinarian_or_provider or ""
            ).strip(),
            cost=cls._as_decimal(cost, "cost"),
            notes=(notes or "").strip(),
            recorded_by=cls._authenticated_user(actor),
        )
        record.full_clean()
        record.save()

        cls._dispatch(
            "AGRICULTURE_HEALTH_RECORDED",
            record,
            actor=actor,
            operation=operation,
            flock=flock,
            record_type=record.record_type,
            medicine_product_id=record.medicine_product_id,
            birds_treated=record.birds_treated,
            cost=str(record.cost),
            finance_posting_required=record.cost > 0,
        )
        return record

    @classmethod
    @transaction.atomic
    def record_mortality(
        cls,
        *,
        flock,
        quantity,
        suspected_cause,
        actor=None,
        operation=None,
        record_date=None,
        health_record=None,
        action_taken="",
        notes="",
    ):
        flock = cls._lock_flock(flock)
        cls._validate_flock_is_operational(flock)
        cls._validate_operation(operation, flock=flock)

        quantity = int(quantity)
        if quantity < 1 or quantity > flock.current_quantity:
            raise ValidationError(
                {
                    "quantity": (
                        "Mortality must be at least one and cannot exceed "
                        "the current flock quantity."
                    )
                }
            )

        record = MortalityRecord(
            operation=operation,
            flock=flock,
            record_date=record_date or timezone.localdate(),
            quantity=quantity,
            suspected_cause=suspected_cause,
            health_record=health_record,
            action_taken=(action_taken or "").strip(),
            notes=(notes or "").strip(),
            recorded_by=cls._authenticated_user(actor),
        )
        record.full_clean()
        record.save()

        flock.current_quantity -= quantity
        flock.save(update_fields=["current_quantity", "updated_at"])

        cls._dispatch(
            "AGRICULTURE_MORTALITY_RECORDED",
            record,
            actor=actor,
            operation=operation,
            flock=flock,
            quantity=quantity,
            suspected_cause=record.suspected_cause,
            remaining_quantity=flock.current_quantity,
        )
        return record

    @classmethod
    @transaction.atomic
    def create_incubation_batch(
        cls,
        *,
        eggs_set,
        set_date,
        expected_hatch_date,
        actor=None,
        operation=None,
        source_flock=None,
        incubator_asset=None,
        chick_product=None,
        output_warehouse=None,
        notes="",
        code="",
    ):
        if source_flock is not None:
            source_flock = cls._lock_flock(source_flock)
            cls._validate_flock_is_operational(source_flock)

        cls._validate_operation(operation, flock=source_flock)

        batch = IncubationBatch(
            code=(code or cls._generate_code("INC", IncubationBatch)).strip(),
            operation=operation,
            source_flock=source_flock,
            incubator_asset=incubator_asset,
            eggs_set=int(eggs_set),
            set_date=set_date,
            expected_hatch_date=expected_hatch_date,
            status="SET",
            chick_product=chick_product,
            output_warehouse=output_warehouse,
            notes=(notes or "").strip(),
        )
        batch.full_clean()
        batch.save()

        from .inventory_integration_service import (
            AgricultureInventoryIntegrationService,
        )

        stock_movement = (
            AgricultureInventoryIntegrationService.receive_chick_output(
                batch=batch,
                actor=actor,
            )
        )

        cls._dispatch(
            "AGRICULTURE_INCUBATION_SET",
            batch,
            actor=actor,
            operation=operation,
            flock=source_flock,
            eggs_set=batch.eggs_set,
            incubator_asset_id=batch.incubator_asset_id,
        )
        return batch

    @classmethod
    @transaction.atomic
    def candle_incubation(
        cls,
        *,
        batch,
        eggs_candled,
        fertile_eggs,
        infertile_eggs,
        actor=None,
        notes="",
    ):
        batch = IncubationBatch.objects.select_for_update().get(pk=batch.pk)
        if batch.status not in {"SET", "CANDLED"}:
            raise ValidationError(
                {"batch": "Only a set incubation batch can be candled."}
            )

        batch.eggs_candled = int(eggs_candled)
        batch.fertile_eggs = int(fertile_eggs)
        batch.infertile_eggs = int(infertile_eggs)
        batch.status = "CANDLED"
        if notes:
            batch.notes = notes.strip()
        batch.full_clean()
        batch.save()

        cls._dispatch(
            "AGRICULTURE_INCUBATION_CANDLED",
            batch,
            actor=actor,
            operation=batch.operation,
            flock=batch.source_flock,
            eggs_candled=batch.eggs_candled,
            fertile_eggs=batch.fertile_eggs,
            infertile_eggs=batch.infertile_eggs,
        )
        return batch

    @classmethod
    @transaction.atomic
    def complete_incubation(
        cls,
        *,
        batch,
        chicks_hatched,
        unhatched_eggs,
        actor=None,
        actual_hatch_date=None,
        notes="",
    ):
        # Lock the batch itself and resolve nullable relations lazily.
        batch = IncubationBatch.objects.select_for_update().get(pk=batch.pk)
        if batch.status not in {"CANDLED", "HATCHING"}:
            raise ValidationError(
                {"batch": "This incubation batch cannot be completed."}
            )

        batch.chicks_hatched = int(chicks_hatched)
        batch.unhatched_eggs = int(unhatched_eggs)
        batch.actual_hatch_date = actual_hatch_date or timezone.localdate()
        batch.status = "COMPLETED"
        if notes:
            batch.notes = notes.strip()
        batch.full_clean()
        batch.save()

        cls._dispatch(
            "AGRICULTURE_CHICKS_HATCHED",
            batch,
            actor=actor,
            operation=batch.operation,
            flock=batch.source_flock,
            chicks_hatched=batch.chicks_hatched,
            unhatched_eggs=batch.unhatched_eggs,
            product_id=batch.chick_product_id,
            warehouse_id=batch.output_warehouse_id,
            inventory_posting_required=bool(
                batch.chick_product_id and batch.output_warehouse_id
            ),
            stock_movement_id=(
                stock_movement.pk if stock_movement is not None else None
            ),
        )
        batch.refresh_from_db()
        return batch

    @classmethod
    @transaction.atomic
    def link_stock_movement(cls, *, record, stock_movement):
        """
        Called by the Inventory event handler after a successful stock posting.
        """
        supported_models = (EggProduction, FeedingRecord, IncubationBatch)
        if not isinstance(record, supported_models):
            raise ValidationError("This record cannot receive a stock movement.")
        if record.stock_movement_id:
            if record.stock_movement_id == stock_movement.pk:
                return record
            raise ValidationError("This record already has a stock movement.")

        locked = record.__class__.objects.select_for_update().get(pk=record.pk)
        if locked.stock_movement_id:
            if locked.stock_movement_id == stock_movement.pk:
                return locked
            raise ValidationError("This record already has a stock movement.")

        locked.stock_movement = stock_movement
        locked.save(update_fields=["stock_movement", "updated_at"])
        return locked