from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from core.event_engine import EventEngine

from inventory.models import Product, StockMovement, StockReservation, Warehouse


class StockService:
    """WPG BOS Inventory Service V2."""

    INBOUND_MOVEMENT_TYPES = {"IN", "TRANSFER_IN", "ADJUSTMENT_IN", "RETURN_IN"}
    OUTBOUND_MOVEMENT_TYPES = {"OUT", "TRANSFER_OUT", "ADJUSTMENT_OUT", "RETURN_OUT"}
    ACTIVE_RESERVATION_STATUSES = {"RESERVED", "PARTIAL"}
    POSTED_STATUS = "POSTED"
    MONEY_QUANTIZER = Decimal("0.01")
    QUANTITY_QUANTIZER = Decimal("0.01")

    @staticmethod
    def _user(actor):
        if actor is None:
            return None
        if hasattr(actor, "is_authenticated"):
            return actor
        return getattr(actor, "user", None)

    @classmethod
    def _decimal(cls, value):
        return Decimal(str(value or 0))

    @classmethod
    def _quantity(cls, value):
        return cls._decimal(value).quantize(cls.QUANTITY_QUANTIZER)

    @classmethod
    def _money(cls, value):
        return cls._decimal(value).quantize(cls.MONEY_QUANTIZER)

    @staticmethod
    def _clean_text(value):
        return (value or "").strip()

    @staticmethod
    def _choice_values(model, field_name):
        field = model._meta.get_field(field_name)
        return {value for value, label in field.choices}

    @classmethod
    def _validate_reference_type(cls, reference_type):
        if reference_type not in cls._choice_values(StockMovement, "reference_type"):
            raise ValidationError("Invalid stock movement reference type.")

    @classmethod
    def _validate_business_unit(cls, business_unit):
        if business_unit and business_unit not in cls._choice_values(StockMovement, "business_unit"):
            raise ValidationError("Invalid stock movement business unit.")

    @classmethod
    def _validate_product(cls, product):
        if product is None or not isinstance(product, Product):
            raise ValidationError("A valid inventory Product is required.")
        if not product.is_active:
            raise ValidationError("Inactive products cannot be used in stock operations.")
        if not product.track_inventory:
            raise ValidationError(f"{product.name} does not track inventory.")

    @classmethod
    def _validate_warehouse(cls, warehouse):
        if warehouse is None or not isinstance(warehouse, Warehouse):
            raise ValidationError("A valid Warehouse is required.")
        if not warehouse.is_active:
            raise ValidationError("Inactive warehouses cannot be used.")

    @classmethod
    def _lock_product_and_warehouse(cls, *, product, warehouse):
        locked_product = Product._base_manager.select_related(None).select_for_update(of=("self",)).get(pk=product.pk)
        locked_warehouse = Warehouse._base_manager.select_related(None).select_for_update(of=("self",)).get(pk=warehouse.pk)
        return locked_product, locked_warehouse

    @classmethod
    def _movement_total(cls, *, product, movement_types, warehouse=None):
        queryset = StockMovement.objects.filter(
            product=product,
            movement_type__in=movement_types,
            status=cls.POSTED_STATUS,
        )
        if warehouse is not None:
            queryset = queryset.filter(warehouse=warehouse)
        return queryset.aggregate(
            total=Coalesce(
                Sum("quantity"),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=18, decimal_places=2)),
            )
        )["total"]

    @classmethod
    def stock_in(cls, *, product, warehouse=None):
        cls._validate_product(product)
        if warehouse is not None:
            cls._validate_warehouse(warehouse)
        return cls._movement_total(product=product, warehouse=warehouse, movement_types=cls.INBOUND_MOVEMENT_TYPES)

    @classmethod
    def stock_out(cls, *, product, warehouse=None):
        cls._validate_product(product)
        if warehouse is not None:
            cls._validate_warehouse(warehouse)
        return cls._movement_total(product=product, warehouse=warehouse, movement_types=cls.OUTBOUND_MOVEMENT_TYPES)

    @classmethod
    def actual_stock(cls, *, product, warehouse=None):
        return cls.stock_in(product=product, warehouse=warehouse) - cls.stock_out(product=product, warehouse=warehouse)

    @classmethod
    def reserved_stock(cls, *, product, warehouse=None):
        cls._validate_product(product)
        if warehouse is not None:
            cls._validate_warehouse(warehouse)
        queryset = StockReservation.objects.filter(product=product, status__in=cls.ACTIVE_RESERVATION_STATUSES)
        if warehouse is not None:
            queryset = queryset.filter(warehouse=warehouse)
        total = Decimal("0.00")
        for row in queryset.values("reserved_quantity", "completed_quantity"):
            remaining = cls._decimal(row["reserved_quantity"]) - cls._decimal(row["completed_quantity"])
            if remaining > 0:
                total += remaining
        return total

    @classmethod
    def available_stock(cls, *, product, warehouse=None):
        return max(
            cls.actual_stock(product=product, warehouse=warehouse)
            - cls.reserved_stock(product=product, warehouse=warehouse),
            Decimal("0.00"),
        )

    @classmethod
    def stock_summary(cls, *, product, warehouse=None):
        actual = cls.actual_stock(product=product, warehouse=warehouse)
        reserved = cls.reserved_stock(product=product, warehouse=warehouse)
        available = max(actual - reserved, Decimal("0.00"))
        reorder_level = cls._decimal(getattr(product, "reorder_level", 0))
        reorder_quantity = cls._decimal(getattr(product, "reorder_quantity", 0))
        return {
            "product": product,
            "warehouse": warehouse,
            "actual_stock": actual,
            "reserved_stock": reserved,
            "available_stock": available,
            "reorder_level": reorder_level,
            "reorder_quantity": reorder_quantity,
            "is_below_reorder_level": available <= reorder_level,
            "inventory_value": actual * cls._money(getattr(product, "standard_cost", 0)),
        }

    @classmethod
    def warehouse_stock_summary(cls, *, product, active_only=True):
        queryset = Warehouse.objects.all()
        if active_only:
            queryset = queryset.filter(is_active=True)
        return [
            cls.stock_summary(product=product, warehouse=warehouse)
            for warehouse in queryset.order_by("warehouse_type", "name")
        ]

    @classmethod
    def _create_movement(
        cls,
        *,
        product,
        warehouse,
        movement_type,
        quantity,
        unit_cost=Decimal("0.00"),
        business_unit="",
        reference_type="OTHER",
        reference_id="",
        reference_no="",
        transfer_group=None,
        reversal_of=None,
        notes="",
        actor=None,
        status="POSTED",
    ):
        if movement_type not in cls._choice_values(StockMovement, "movement_type"):
            raise ValidationError("Invalid stock movement type.")
        if status not in cls._choice_values(StockMovement, "status"):
            raise ValidationError("Invalid stock movement status.")
        cls._validate_reference_type(reference_type)
        cls._validate_business_unit(business_unit)
        quantity = cls._quantity(quantity)
        unit_cost = cls._money(unit_cost)
        if quantity <= 0:
            raise ValidationError("Stock movement quantity must be greater than zero.")
        if unit_cost < 0:
            raise ValidationError("Unit cost cannot be negative.")

        movement = StockMovement(
            product=product,
            warehouse=warehouse,
            movement_type=movement_type,
            status=status,
            quantity=quantity,
            unit_cost=unit_cost,
            business_unit=business_unit or product.business_unit or warehouse.business_unit or "",
            reference_type=reference_type,
            reference_id=cls._clean_text(reference_id),
            reference_no=cls._clean_text(reference_no),
            transfer_group=transfer_group,
            reversal_of=reversal_of,
            notes=cls._clean_text(notes),
            created_by=cls._user(actor),
        )
        movement.full_clean()
        movement.save()
        return movement

    @classmethod
    def _dispatch_movement_event(cls, *, movement, actor, event_code, title, message, level="INFO", metadata=None):
        event_metadata = {
            "movement_id": movement.pk,
            "product_id": movement.product_id,
            "product_name": movement.product.name,
            "warehouse_id": movement.warehouse_id,
            "warehouse_name": movement.warehouse.name,
            "movement_type": movement.movement_type,
            "status": movement.status,
            "quantity": str(movement.quantity),
            "unit_cost": str(movement.unit_cost),
            "total_cost": str(movement.total_cost),
            "business_unit": movement.business_unit,
            "reference_type": movement.reference_type,
            "reference_id": movement.reference_id,
            "reference_no": movement.reference_no,
        }
        if metadata:
            event_metadata.update(metadata)
        EventEngine.dispatch(
            event_code=event_code,
            actor=cls._user(actor),
            obj=movement,
            title=title,
            message=message,
            level=level,
            metadata=event_metadata,
            notify_groups=["Inventory Manager"],
            notify_owner=True,
        )

    @classmethod
    @transaction.atomic
    def receive_stock(
        cls,
        *,
        product,
        warehouse,
        quantity,
        unit_cost=None,
        business_unit="",
        reference_type="OTHER",
        reference_id="",
        reference_no="",
        notes="",
        actor=None,
        movement_type="IN",
    ):
        cls._validate_product(product)
        cls._validate_warehouse(warehouse)
        if movement_type not in {"IN", "RETURN_IN"}:
            raise ValidationError("receive_stock() only accepts IN or RETURN_IN.")
        product, warehouse = cls._lock_product_and_warehouse(product=product, warehouse=warehouse)
        movement = cls._create_movement(
            product=product,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=product.standard_cost if unit_cost is None else unit_cost,
            business_unit=business_unit,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_no=reference_no,
            notes=notes,
            actor=actor,
        )
        cls._dispatch_movement_event(
            movement=movement,
            actor=actor,
            event_code="INVENTORY_STOCK_RECEIVED",
            title="Stock Received",
            message=f"{movement.quantity} {movement.product.unit} of {movement.product.name} received into {movement.warehouse.name}.",
            level="SUCCESS",
        )
        return movement

    @classmethod
    @transaction.atomic
    def issue_stock(
        cls,
        *,
        product,
        warehouse,
        quantity,
        unit_cost=None,
        business_unit="",
        reference_type="OTHER",
        reference_id="",
        reference_no="",
        notes="",
        actor=None,
        movement_type="OUT",
        include_reserved_stock=False,
    ):
        cls._validate_product(product)
        cls._validate_warehouse(warehouse)
        if movement_type not in {"OUT", "RETURN_OUT"}:
            raise ValidationError("issue_stock() only accepts OUT or RETURN_OUT.")
        product, warehouse = cls._lock_product_and_warehouse(product=product, warehouse=warehouse)
        quantity = cls._quantity(quantity)
        if quantity <= 0:
            raise ValidationError("Issue quantity must be greater than zero.")
        stock_to_check = (
            cls.actual_stock(product=product, warehouse=warehouse)
            if include_reserved_stock
            else cls.available_stock(product=product, warehouse=warehouse)
        )
        negative_stock_allowed = product.allow_negative_stock or warehouse.allow_negative_stock
        if not negative_stock_allowed and quantity > stock_to_check:
            stock_name = "physical stock" if include_reserved_stock else "available stock"
            raise ValidationError(
                f"Insufficient {stock_name}. Requested: {quantity}; available: {stock_to_check}."
            )
        movement = cls._create_movement(
            product=product,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=product.standard_cost if unit_cost is None else unit_cost,
            business_unit=business_unit,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_no=reference_no,
            notes=notes,
            actor=actor,
        )
        cls._dispatch_movement_event(
            movement=movement,
            actor=actor,
            event_code="INVENTORY_STOCK_ISSUED",
            title="Stock Issued",
            message=f"{movement.quantity} {movement.product.unit} of {movement.product.name} issued from {movement.warehouse.name}.",
            level="SUCCESS",
        )
        return movement

    @classmethod
    @transaction.atomic
    def transfer_stock(
        cls,
        *,
        product,
        source_warehouse,
        destination_warehouse,
        quantity,
        unit_cost=None,
        business_unit="",
        reference_id="",
        reference_no="",
        notes="",
        actor=None,
    ):
        cls._validate_product(product)
        cls._validate_warehouse(source_warehouse)
        cls._validate_warehouse(destination_warehouse)
        if source_warehouse.pk == destination_warehouse.pk:
            raise ValidationError("Source and destination warehouses must be different.")
        quantity = cls._quantity(quantity)
        if quantity <= 0:
            raise ValidationError("Transfer quantity must be greater than zero.")

        warehouse_ids = sorted([source_warehouse.pk, destination_warehouse.pk])
        locked_warehouses = {
            warehouse.pk: warehouse
            for warehouse in Warehouse._base_manager.select_related(None)
            .select_for_update(of=("self",))
            .filter(pk__in=warehouse_ids)
            .order_by("pk")
        }
        product = Product._base_manager.select_related(None).select_for_update(of=("self",)).get(pk=product.pk)
        source_warehouse = locked_warehouses[source_warehouse.pk]
        destination_warehouse = locked_warehouses[destination_warehouse.pk]

        actual = cls.actual_stock(product=product, warehouse=source_warehouse)
        negative_stock_allowed = product.allow_negative_stock or source_warehouse.allow_negative_stock
        if not negative_stock_allowed and quantity > actual:
            raise ValidationError(
                f"Insufficient physical stock for transfer. Requested: {quantity}; physical stock: {actual}."
            )

        transfer_group = uuid.uuid4()
        resolved_unit_cost = product.standard_cost if unit_cost is None else unit_cost
        transfer_out = cls._create_movement(
            product=product,
            warehouse=source_warehouse,
            movement_type="TRANSFER_OUT",
            quantity=quantity,
            unit_cost=resolved_unit_cost,
            business_unit=business_unit,
            reference_type="TRANSFER",
            reference_id=reference_id,
            reference_no=reference_no,
            transfer_group=transfer_group,
            notes=notes,
            actor=actor,
        )
        transfer_in = cls._create_movement(
            product=product,
            warehouse=destination_warehouse,
            movement_type="TRANSFER_IN",
            quantity=quantity,
            unit_cost=resolved_unit_cost,
            business_unit=business_unit,
            reference_type="TRANSFER",
            reference_id=reference_id,
            reference_no=reference_no,
            transfer_group=transfer_group,
            notes=notes,
            actor=actor,
        )
        cls._dispatch_movement_event(
            movement=transfer_out,
            actor=actor,
            event_code="INVENTORY_STOCK_TRANSFERRED",
            title="Stock Transferred",
            message=f"{quantity} {product.unit} of {product.name} transferred from {source_warehouse.name} to {destination_warehouse.name}.",
            level="SUCCESS",
            metadata={
                "transfer_group": str(transfer_group),
                "source_warehouse_id": source_warehouse.pk,
                "destination_warehouse_id": destination_warehouse.pk,
                "transfer_in_movement_id": transfer_in.pk,
            },
        )
        return {
            "product": product,
            "source_warehouse": source_warehouse,
            "destination_warehouse": destination_warehouse,
            "quantity": quantity,
            "transfer_group": transfer_group,
            "transfer_out": transfer_out,
            "transfer_in": transfer_in,
        }

    @classmethod
    @transaction.atomic
    def adjust_stock(
        cls,
        *,
        product,
        warehouse,
        quantity,
        direction,
        unit_cost=None,
        business_unit="",
        reference_type="ADJUSTMENT",
        reference_id="",
        reference_no="",
        notes="",
        actor=None,
    ):
        direction = (direction or "").strip().upper()
        if direction not in {"IN", "OUT"}:
            raise ValidationError("Adjustment direction must be 'IN' or 'OUT'.")
        movement_type = "ADJUSTMENT_IN" if direction == "IN" else "ADJUSTMENT_OUT"
        cls._validate_product(product)
        cls._validate_warehouse(warehouse)
        product, warehouse = cls._lock_product_and_warehouse(product=product, warehouse=warehouse)
        quantity = cls._quantity(quantity)
        if quantity <= 0:
            raise ValidationError("Adjustment quantity must be greater than zero.")
        if direction == "OUT":
            actual = cls.actual_stock(product=product, warehouse=warehouse)
            negative_stock_allowed = product.allow_negative_stock or warehouse.allow_negative_stock
            if not negative_stock_allowed and quantity > actual:
                raise ValidationError(
                    f"Negative adjustment exceeds physical stock. Requested: {quantity}; physical stock: {actual}."
                )
        movement = cls._create_movement(
            product=product,
            warehouse=warehouse,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=product.standard_cost if unit_cost is None else unit_cost,
            business_unit=business_unit,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_no=reference_no,
            notes=notes,
            actor=actor,
        )
        cls._dispatch_movement_event(
            movement=movement,
            actor=actor,
            event_code="INVENTORY_STOCK_ADJUSTED",
            title="Stock Adjusted",
            message=f"{movement.product.name} stock adjusted {direction} by {movement.quantity} {movement.product.unit} at {movement.warehouse.name}.",
            level="WARNING",
            metadata={"adjustment_direction": direction},
        )
        return movement

    @classmethod
    @transaction.atomic
    def reverse_movement(cls, *, movement, actor=None, reason=""):
        if movement is None or not getattr(movement, "pk", None):
            raise ValidationError("A saved stock movement is required.")
        movement = (
            StockMovement._base_manager.select_related(None)
            .select_for_update(of=("self",))
            .select_related("product", "warehouse")
            .get(pk=movement.pk)
        )
        if movement.status != "POSTED":
            raise ValidationError("Only posted movements can be reversed.")
        if movement.reversal_of_id:
            raise ValidationError("A reversal movement cannot be reversed again.")
        try:
            movement.reversal_movement
        except StockMovement.DoesNotExist:
            pass
        else:
            raise ValidationError("This movement has already been reversed.")
        if movement.movement_type in {"TRANSFER_IN", "TRANSFER_OUT"}:
            raise ValidationError("Transfer movements must be reversed using reverse_transfer().")

        opposite_type = {
            "IN": "OUT",
            "OUT": "IN",
            "ADJUSTMENT_IN": "ADJUSTMENT_OUT",
            "ADJUSTMENT_OUT": "ADJUSTMENT_IN",
            "RETURN_IN": "RETURN_OUT",
            "RETURN_OUT": "RETURN_IN",
        }.get(movement.movement_type)
        if not opposite_type:
            raise ValidationError("This stock movement type cannot be reversed.")

        product, warehouse = cls._lock_product_and_warehouse(
            product=movement.product,
            warehouse=movement.warehouse,
        )
        reason = cls._clean_text(reason)
        reversal_notes = f"Reversal of movement #{movement.pk}."
        if reason:
            reversal_notes = f"{reversal_notes} Reason: {reason}"
        reversal = cls._create_movement(
            product=product,
            warehouse=warehouse,
            movement_type=opposite_type,
            quantity=movement.quantity,
            unit_cost=movement.unit_cost,
            business_unit=movement.business_unit,
            reference_type=movement.reference_type,
            reference_id=movement.reference_id,
            reference_no=movement.reference_no,
            reversal_of=movement,
            notes=reversal_notes,
            actor=actor,
        )
        movement.status = "REVERSED"
        movement.save(update_fields=["status", "updated_at"])
        cls._dispatch_movement_event(
            movement=reversal,
            actor=actor,
            event_code="INVENTORY_MOVEMENT_REVERSED",
            title="Stock Movement Reversed",
            message=f"Stock movement #{movement.pk} was reversed by movement #{reversal.pk}.",
            level="WARNING",
            metadata={
                "original_movement_id": movement.pk,
                "reversal_movement_id": reversal.pk,
                "reason": reason,
            },
        )
        return reversal

    @classmethod
    @transaction.atomic
    def reverse_transfer(cls, *, transfer_group, actor=None, reason=""):
        if not transfer_group:
            raise ValidationError("Transfer group is required.")
        movements = list(
            StockMovement.objects.select_for_update()
            .select_related("product", "warehouse")
            .filter(transfer_group=transfer_group, status="POSTED")
            .order_by("pk")
        )
        if len(movements) != 2:
            raise ValidationError("A valid transfer must have exactly two posted movements.")
        transfer_out = next((m for m in movements if m.movement_type == "TRANSFER_OUT"), None)
        transfer_in = next((m for m in movements if m.movement_type == "TRANSFER_IN"), None)
        if not transfer_out or not transfer_in:
            raise ValidationError("The transfer group is incomplete.")
        if transfer_out.product_id != transfer_in.product_id:
            raise ValidationError("Transfer movements must reference the same product.")

        reverse_result = cls.transfer_stock(
            product=transfer_out.product,
            source_warehouse=transfer_in.warehouse,
            destination_warehouse=transfer_out.warehouse,
            quantity=transfer_out.quantity,
            unit_cost=transfer_out.unit_cost,
            business_unit=transfer_out.business_unit,
            reference_id=transfer_out.reference_id,
            reference_no=transfer_out.reference_no,
            notes=(f"Reversal of transfer {transfer_group}. {cls._clean_text(reason)}").strip(),
            actor=actor,
        )
        for movement in movements:
            movement.status = "REVERSED"
            movement.save(update_fields=["status", "updated_at"])
        return {
            "original_transfer_group": transfer_group,
            "reversal": reverse_result,
        }
