from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from core.event_engine import EventEngine
from inventory.models import StockMovement
   

from furniture.models import (
    BillOfMaterial,
    ProductionJob,
    ProductionMaterial,
    ProductionOutput,
    StockReservation,
    ProductionTimeline,
)


class FurnitureInventoryService:
    """
    Furniture-to-Inventory integration service.

    Responsibilities:
    - calculate stock balances from StockMovement
    - check raw-material availability
    - reserve materials from BOM
    - release reservations
    - issue reserved materials to production
    - record direct material consumption
    - receive finished products into inventory
    """

    ZERO = Decimal("0.00")

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    @staticmethod
    def _to_decimal(value):
        if value is None:
            return Decimal("0.00")

        if isinstance(value, Decimal):
            return value

        return Decimal(str(value))

    @staticmethod
    def _actor(employee_or_user):
        """
        Return accounts.User from either User or Employee.
        """
        if employee_or_user is None:
            return None

        if hasattr(employee_or_user, "is_authenticated"):
            return employee_or_user

        return getattr(
            employee_or_user,
            "user",
            None,
        )

    @staticmethod
    def _employee(employee_or_user):
        """
        Return Employee from either Employee or User.
        """
        if employee_or_user is None:
            return None

        if hasattr(employee_or_user, "employee_code"):
            return employee_or_user

        return getattr(
            employee_or_user,
            "employee",
            None,
        )

    @staticmethod
    def _add_timeline(
        production_job,
        action,
        performed_by=None,
        note="",
    ):
        return ProductionTimeline.objects.create(
            production_job=production_job,
            action=action,
            from_status=production_job.status,
            to_status=production_job.status,
            performed_by=FurnitureInventoryService._employee(
                performed_by
            ),
            note=note or "",
        )

    # =====================================================
    # STOCK BALANCE
    # =====================================================

    @classmethod
    def raw_material_stock(
        cls,
        raw_material,
        warehouse=None,
    ):
        movements = StockMovement.objects.filter(
            raw_material=raw_material,
        )

        if warehouse is not None:
            movements = movements.filter(
                warehouse=warehouse,
            )

        stock_in = movements.filter(
            movement_type="IN",
        ).aggregate(
            total=Coalesce(
                Sum("quantity"),
                cls.ZERO,
                output_field=DecimalField(
                    max_digits=18,
                    decimal_places=2,
                ),
            )
        )["total"]

        stock_out = movements.filter(
            movement_type="OUT",
        ).aggregate(
            total=Coalesce(
                Sum("quantity"),
                cls.ZERO,
                output_field=DecimalField(
                    max_digits=18,
                    decimal_places=2,
                ),
            )
        )["total"]

        adjustments = movements.filter(
            movement_type="ADJUSTMENT",
        ).aggregate(
            total=Coalesce(
                Sum("quantity"),
                cls.ZERO,
                output_field=DecimalField(
                    max_digits=18,
                    decimal_places=2,
                ),
            )
        )["total"]

        return (
            cls._to_decimal(stock_in)
            - cls._to_decimal(stock_out)
            + cls._to_decimal(adjustments)
        )

    @classmethod
    def product_stock(
        cls,
        product,
        warehouse=None,
    ):
        movements = StockMovement.objects.filter(
            product=product,
        )

        if warehouse is not None:
            movements = movements.filter(
                warehouse=warehouse,
            )

        stock_in = movements.filter(
            movement_type="IN",
        ).aggregate(
            total=Coalesce(
                Sum("quantity"),
                cls.ZERO,
                output_field=DecimalField(
                    max_digits=18,
                    decimal_places=2,
                ),
            )
        )["total"]

        stock_out = movements.filter(
            movement_type="OUT",
        ).aggregate(
            total=Coalesce(
                Sum("quantity"),
                cls.ZERO,
                output_field=DecimalField(
                    max_digits=18,
                    decimal_places=2,
                ),
            )
        )["total"]

        adjustments = movements.filter(
            movement_type="ADJUSTMENT",
        ).aggregate(
            total=Coalesce(
                Sum("quantity"),
                cls.ZERO,
                output_field=DecimalField(
                    max_digits=18,
                    decimal_places=2,
                ),
            )
        )["total"]

        return (
            cls._to_decimal(stock_in)
            - cls._to_decimal(stock_out)
            + cls._to_decimal(adjustments)
        )

    # =====================================================
    # RESERVED STOCK
    # =====================================================

    @classmethod
    def reserved_quantity(
        cls,
        raw_material,
        exclude_job=None,
    ):
        reservations = StockReservation.objects.filter(
            raw_material=raw_material,
            status="reserved",
        )

        if exclude_job is not None:
            reservations = reservations.exclude(
                production_job=exclude_job,
            )

        return reservations.aggregate(
            total=Coalesce(
                Sum("quantity"),
                cls.ZERO,
                output_field=DecimalField(
                    max_digits=18,
                    decimal_places=2,
                ),
            )
        )["total"]

    @classmethod
    def available_raw_material_stock(
        cls,
        raw_material,
        warehouse=None,
        exclude_job=None,
    ):
        physical_stock = cls.raw_material_stock(
            raw_material=raw_material,
            warehouse=warehouse,
        )

        reserved_stock = cls.reserved_quantity(
            raw_material=raw_material,
            exclude_job=exclude_job,
        )

        return physical_stock - reserved_stock

    # =====================================================
    # MATERIAL REQUIREMENTS
    # =====================================================

    @classmethod
    def material_requirements(cls, production_job):
        """
        Calculate materials required from the product BOM.

        Required quantity:
        BOM quantity per unit × production job quantity.
        """
        if not production_job.product:
            raise ValidationError(
                "Production job has no product selected."
            )

        bom_items = BillOfMaterial.objects.filter(
            product=production_job.product,
        ).select_related(
            "raw_material",
        )

        requirements = []

        for item in bom_items:
            quantity_required = (
                cls._to_decimal(item.quantity_required)
                * cls._to_decimal(
                    production_job.quantity_to_produce
                )
            )

            requirements.append(
                {
                    "bom": item,
                    "raw_material": item.raw_material,
                    "quantity_required": quantity_required,
                    "unit_cost": cls._to_decimal(
                        item.raw_material.unit_cost
                    ),
                    "total_cost": (
                        quantity_required
                        * cls._to_decimal(
                            item.raw_material.unit_cost
                        )
                    ),
                }
            )

        return requirements

    @classmethod
    def check_material_availability(
        cls,
        production_job,
        warehouse=None,
    ):
        result = {
            "available": True,
            "items": [],
            "shortages": [],
        }

        requirements = cls.material_requirements(
            production_job
        )

        if not requirements:
            result["available"] = False
            result["shortages"].append(
                {
                    "message": (
                        "No Bill of Material is configured "
                        "for this product."
                    )
                }
            )

            return result

        for requirement in requirements:
            raw_material = requirement["raw_material"]
            required = requirement["quantity_required"]

            available = cls.available_raw_material_stock(
                raw_material=raw_material,
                warehouse=warehouse,
                exclude_job=production_job,
            )

            shortage = max(
                required - available,
                cls.ZERO,
            )

            item_result = {
                **requirement,
                "available_stock": available,
                "shortage": shortage,
                "is_available": shortage <= 0,
            }

            result["items"].append(item_result)

            if shortage > 0:
                result["available"] = False
                result["shortages"].append(
                    item_result
                )

        return result

    # =====================================================
    # RESERVE MATERIALS
    # =====================================================

    @classmethod
    @transaction.atomic
    def reserve_materials(
        cls,
        production_job,
        warehouse=None,
        performed_by=None,
    ):
        if production_job.status not in {
            "ORDER_CONFIRMED",
            "MATERIAL_RESERVED",
        }:
            raise ValidationError(
                "Materials can only be reserved for a confirmed order."
            )

        availability = cls.check_material_availability(
            production_job=production_job,
            warehouse=warehouse,
        )

        if not availability["available"]:
            shortage_messages = []

            for item in availability["shortages"]:
                if "raw_material" not in item:
                    shortage_messages.append(
                        item["message"]
                    )
                    continue

                shortage_messages.append(
                    (
                        f"{item['raw_material']}: "
                        f"required {item['quantity_required']}, "
                        f"available {item['available_stock']}, "
                        f"shortage {item['shortage']}."
                    )
                )

            raise ValidationError(
                shortage_messages
            )

        StockReservation.objects.filter(
            production_job=production_job,
            status="reserved",
        ).delete()

        reservations = []

        for item in availability["items"]:
            reservation = StockReservation.objects.create(
                production_job=production_job,
                raw_material=item["raw_material"],
                quantity=item["quantity_required"],
                status="reserved",
            )

            reservations.append(reservation)

        old_status = production_job.status
        production_job.status = "MATERIAL_RESERVED"
        production_job.save(
            update_fields=["status"]
        )

        cls._add_timeline(
            production_job=production_job,
            action="Materials reserved",
            performed_by=performed_by,
            note=(
                f"{len(reservations)} material reservation(s) "
                "created successfully."
            ),
        )

        EventEngine.dispatch(
            event_code="FURNITURE_MATERIALS_RESERVED",
            actor=cls._actor(performed_by),
            obj=production_job,
            title="Production Materials Reserved",
            message=(
                f"Materials were reserved for production job "
                f"#{production_job.id}."
            ),
            level="SUCCESS",
            metadata={
                "production_job_id": production_job.id,
                "from_status": old_status,
                "to_status": production_job.status,
                "reservation_count": len(reservations),
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
                "Store Keeper",
            ],
            notify_owner=True,
        )

        return reservations

    # =====================================================
    # RELEASE RESERVATIONS
    # =====================================================

    @classmethod
    @transaction.atomic
    def release_reservations(
        cls,
        production_job,
        performed_by=None,
        note="",
    ):
        reservations = StockReservation.objects.filter(
            production_job=production_job,
            status="reserved",
        )

        released_count = reservations.update(
            status="released"
        )

        cls._add_timeline(
            production_job=production_job,
            action="Material reservations released",
            performed_by=performed_by,
            note=(
                note
                or f"{released_count} reservation(s) released."
            ),
        )

        EventEngine.dispatch(
            event_code="FURNITURE_RESERVATIONS_RELEASED",
            actor=cls._actor(performed_by),
            obj=production_job,
            title="Material Reservations Released",
            message=(
                f"Reservations for production job "
                f"#{production_job.id} were released."
            ),
            level="WARNING",
            metadata={
                "production_job_id": production_job.id,
                "released_count": released_count,
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
                "Store Keeper",
            ],
        )

        return released_count

    # =====================================================
    # ISSUE MATERIALS TO PRODUCTION
    # =====================================================

    @classmethod
    @transaction.atomic
    def issue_reserved_materials(
        cls,
        production_job,
        warehouse,
        performed_by=None,
    ):
        if warehouse is None:
            raise ValidationError(
                "Warehouse is required when issuing materials."
            )

        reservations = list(
            StockReservation.objects.select_for_update()
            .filter(
                production_job=production_job,
                status="reserved",
            )
            .select_related("raw_material")
        )

        if not reservations:
            raise ValidationError(
                "No active material reservations were found."
            )

        movements = []

        for reservation in reservations:
            current_stock = cls.raw_material_stock(
                raw_material=reservation.raw_material,
                warehouse=warehouse,
            )

            if current_stock < reservation.quantity:
                raise ValidationError(
                    (
                        f"Insufficient stock for "
                        f"{reservation.raw_material}. "
                        f"Available: {current_stock}; "
                        f"required: {reservation.quantity}."
                    )
                )

            movement = StockMovement.objects.create(
                product=None,
                raw_material=reservation.raw_material,
                movement_type="OUT",
                quantity=reservation.quantity,
                unit_cost=reservation.raw_material.unit_cost,
                reference_no=(
                    f"FURN-JOB-{production_job.id}-ISSUE"
                ),
                warehouse=warehouse,
                created_by=cls._actor(performed_by),
            )

            ProductionMaterial.objects.create(
                production_job=production_job,
                raw_material=reservation.raw_material,
                quantity_used=reservation.quantity,
                unit_cost=reservation.raw_material.unit_cost,
            )

            reservation.status = "issued"
            reservation.save(
                update_fields=["status"]
            )

            movements.append(movement)

        cls._add_timeline(
            production_job=production_job,
            action="Reserved materials issued",
            performed_by=performed_by,
            note=(
                f"{len(movements)} stock-out movement(s) "
                "recorded."
            ),
        )

        EventEngine.dispatch(
            event_code="FURNITURE_MATERIALS_ISSUED",
            actor=cls._actor(performed_by),
            obj=production_job,
            title="Materials Issued to Production",
            message=(
                f"Reserved materials were issued for "
                f"production job #{production_job.id}."
            ),
            level="INFO",
            metadata={
                "production_job_id": production_job.id,
                "movement_count": len(movements),
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
                "Store Keeper",
            ],
            notify_owner=True,
        )

        return movements

    # =====================================================
    # DIRECT MATERIAL USAGE
    # =====================================================

    @classmethod
    @transaction.atomic
    def record_material_usage(
        cls,
        production_job,
        raw_material,
        quantity,
        warehouse,
        performed_by=None,
        unit_cost=None,
    ):
        quantity = cls._to_decimal(quantity)

        if quantity <= 0:
            raise ValidationError(
                "Material quantity must be greater than zero."
            )

        available = cls.raw_material_stock(
            raw_material=raw_material,
            warehouse=warehouse,
        )

        if available < quantity:
            raise ValidationError(
                (
                    f"Insufficient stock for {raw_material}. "
                    f"Available: {available}; required: {quantity}."
                )
            )

        cost = cls._to_decimal(
            unit_cost
            if unit_cost is not None
            else raw_material.unit_cost
        )

        movement = StockMovement.objects.create(
            product=None,
            raw_material=raw_material,
            movement_type="OUT",
            quantity=quantity,
            unit_cost=cost,
            reference_no=(
                f"FURN-JOB-{production_job.id}-MATERIAL"
            ),
            warehouse=warehouse,
            created_by=cls._actor(performed_by),
        )

        consumption = ProductionMaterial.objects.create(
            production_job=production_job,
            raw_material=raw_material,
            quantity_used=quantity,
            unit_cost=cost,
        )

        cls._add_timeline(
            production_job=production_job,
            action="Material consumed",
            performed_by=performed_by,
            note=(
                f"{quantity} {raw_material.unit} of "
                f"{raw_material} consumed."
            ),
        )

        return {
            "movement": movement,
            "consumption": consumption,
        }

    # =====================================================
    # RECEIVE FINISHED GOODS
    # =====================================================

    @classmethod
    @transaction.atomic
    def receive_finished_goods(
        cls,
        production_job,
        product,
        quantity,
        warehouse,
        performed_by=None,
        unit_cost=None,
        image=None,
    ):
        quantity = cls._to_decimal(quantity)

        if quantity <= 0:
            raise ValidationError(
                "Finished-goods quantity must be greater than zero."
            )

        if warehouse is None:
            raise ValidationError(
                "Warehouse is required when receiving finished goods."
            )

        if production_job.status not in {
            "QUALITY_CHECK",
            "FINISHED_GOODS",
        }:
            raise ValidationError(
                (
                    "Finished goods can only be received after "
                    "production reaches quality check."
                )
            )

        cost = cls._to_decimal(
            unit_cost
            if unit_cost is not None
            else Decimal("0.00")
        )

        output = ProductionOutput.objects.create(
            production_job=production_job,
            product=product,
            quantity_produced=int(quantity),
            image=image,
            produced_by=cls._employee(performed_by),
        )

        movement = StockMovement.objects.create(
            product=product,
            raw_material=None,
            movement_type="IN",
            quantity=quantity,
            unit_cost=cost,
            reference_no=(
                f"FURN-JOB-{production_job.id}-FINISHED"
            ),
            warehouse=warehouse,
            created_by=cls._actor(performed_by),
        )

        old_status = production_job.status
        production_job.status = "FINISHED_GOODS"
        production_job.save(
            update_fields=["status"]
        )

        cls._add_timeline(
            production_job=production_job,
            action="Finished goods received into stock",
            performed_by=performed_by,
            note=(
                f"{quantity} unit(s) of {product} "
                "received into inventory."
            ),
        )

        EventEngine.dispatch(
            event_code="FURNITURE_FINISHED_GOODS_RECEIVED",
            actor=cls._actor(performed_by),
            obj=production_job,
            title="Finished Goods Received",
            message=(
                f"{quantity} unit(s) from production job "
                f"#{production_job.id} were received into stock."
            ),
            level="SUCCESS",
            metadata={
                "production_job_id": production_job.id,
                "product_id": product.id,
                "output_id": output.id,
                "stock_movement_id": movement.id,
                "quantity": str(quantity),
                "from_status": old_status,
                "to_status": production_job.status,
            },
            notify_groups=[
                "Furniture Manager",
                "Production Supervisor",
                "Store Keeper",
            ],
            notify_owner=True,
        )

        return {
            "output": output,
            "movement": movement,
        }