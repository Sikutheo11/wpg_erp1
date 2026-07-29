from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db.models import Sum

from inventory.models import Product, Warehouse
from inventory.services.stock_service import StockService

from ..models import EggProduction, IncubationBatch, PoultryFlock


class AgricultureValuationService:
    """
    Read-only valuation service for Poultry biological assets and egg stock.

    The first implementation uses a cost model:
    - flock value = current birds × average unit cost;
    - egg stock value = physical stock × Inventory product standard cost;
    - mortality loss = dead birds × flock average unit cost;
    - production indicators allocate recorded feed and health costs.

    Finance remains the accounting ledger; this service provides calculated
    values and does not create journal entries.
    """

    BUSINESS_UNIT = "AGRICULTURE"
    MONEY_PLACES = Decimal("0.01")
    QUANTITY_PLACES = Decimal("0.001")

    @classmethod
    def _decimal(cls, value):
        if value is None:
            return Decimal("0")
        return Decimal(str(value))

    @classmethod
    def _money(cls, value):
        return cls._decimal(value).quantize(
            cls.MONEY_PLACES,
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def _quantity(cls, value):
        return cls._decimal(value).quantize(
            cls.QUANTITY_PLACES,
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def _saved(instance, expected_model, field_name):
        if instance is None or not isinstance(instance, expected_model):
            raise ValidationError(
                {field_name: f"A valid {expected_model.__name__} is required."}
            )
        if not instance.pk:
            raise ValidationError(
                {field_name: f"The {expected_model.__name__} must be saved."}
            )

    @staticmethod
    def _date_range(queryset, start_date=None, end_date=None):
        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                {"end_date": "End date cannot precede start date."}
            )
        if start_date:
            queryset = queryset.filter(record_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(record_date__lte=end_date)
        return queryset

    @classmethod
    def flock_valuation(
        cls,
        *,
        flock,
        start_date=None,
        end_date=None,
    ):
        cls._saved(flock, PoultryFlock, "flock")

        average_unit_cost = cls._money(flock.average_unit_cost)
        initial_value = cls._money(
            cls._decimal(flock.initial_quantity) * average_unit_cost
        )
        current_value = cls._money(
            cls._decimal(flock.current_quantity) * average_unit_cost
        )

        mortality_records = cls._date_range(
            flock.mortality_records.all(),
            start_date=start_date,
            end_date=end_date,
        )
        mortality_quantity = (
            mortality_records.aggregate(total=Sum("quantity"))["total"] or 0
        )
        mortality_loss = cls._money(
            cls._decimal(mortality_quantity) * average_unit_cost
        )

        feeding_records = cls._date_range(
            flock.feeding_records.all(),
            start_date=start_date,
            end_date=end_date,
        )
        feed_quantity_kg = Decimal("0")
        feed_cost = Decimal("0")
        for record in feeding_records.only("quantity_kg", "unit_cost"):
            feed_quantity_kg += cls._decimal(record.quantity_kg)
            feed_cost += cls._decimal(record.total_cost)

        health_records = cls._date_range(
            flock.health_records.all(),
            start_date=start_date,
            end_date=end_date,
        )
        health_cost = cls._decimal(
            health_records.aggregate(total=Sum("cost"))["total"]
        )

        eggs = cls._date_range(
            flock.egg_production_records.all(),
            start_date=start_date,
            end_date=end_date,
        )
        egg_totals = eggs.aggregate(
            collected=Sum("eggs_collected"),
            saleable=Sum("saleable_eggs"),
            hatching=Sum("hatching_eggs"),
            cracked=Sum("cracked_eggs"),
            rejected=Sum("dirty_or_rejected_eggs"),
        )
        eggs_collected = egg_totals["collected"] or 0

        operating_cost = cls._money(feed_cost + health_cost)
        cost_per_current_bird = (
            cls._money(
                operating_cost / cls._decimal(flock.current_quantity)
            )
            if flock.current_quantity
            else Decimal("0.00")
        )
        operating_cost_per_egg = (
            cls._money(
                operating_cost / cls._decimal(eggs_collected)
            )
            if eggs_collected
            else Decimal("0.00")
        )

        return {
            "flock": flock,
            "flock_id": flock.pk,
            "flock_code": flock.code,
            "purpose": flock.purpose,
            "status": flock.status,
            "initial_quantity": flock.initial_quantity,
            "current_quantity": flock.current_quantity,
            "average_unit_cost": average_unit_cost,
            "initial_biological_asset_value": initial_value,
            "current_biological_asset_value": current_value,
            "mortality_quantity": mortality_quantity,
            "mortality_loss": mortality_loss,
            "feed_quantity_kg": cls._quantity(feed_quantity_kg),
            "feed_cost": cls._money(feed_cost),
            "health_cost": cls._money(health_cost),
            "operating_cost": operating_cost,
            "operating_cost_per_current_bird": cost_per_current_bird,
            "eggs_collected": eggs_collected,
            "saleable_eggs": egg_totals["saleable"] or 0,
            "hatching_eggs": egg_totals["hatching"] or 0,
            "cracked_eggs": egg_totals["cracked"] or 0,
            "rejected_eggs": egg_totals["rejected"] or 0,
            "operating_cost_per_egg": operating_cost_per_egg,
            "start_date": start_date,
            "end_date": end_date,
        }

    @classmethod
    def egg_inventory_valuation(
        cls,
        *,
        product=None,
        warehouse=None,
    ):
        if product is not None:
            cls._saved(product, Product, "product")
            if getattr(product, "business_unit", "") != cls.BUSINESS_UNIT:
                raise ValidationError(
                    {"product": "The egg product must belong to Agriculture."}
                )

        if warehouse is not None:
            cls._saved(warehouse, Warehouse, "warehouse")
            business_unit = getattr(warehouse, "business_unit", "")
            if business_unit and business_unit != cls.BUSINESS_UNIT:
                raise ValidationError(
                    {
                        "warehouse": (
                            "The warehouse must belong to Agriculture."
                        )
                    }
                )

        pairs = EggProduction.objects.exclude(
            inventory_product=None
        ).exclude(
            warehouse=None
        )
        if product is not None:
            pairs = pairs.filter(inventory_product=product)
        if warehouse is not None:
            pairs = pairs.filter(warehouse=warehouse)

        pair_ids = pairs.values_list(
            "inventory_product_id",
            "warehouse_id",
        ).distinct()

        lines = []
        total_quantity = Decimal("0")
        total_value = Decimal("0")

        for product_id, warehouse_id in pair_ids:
            egg_product = Product.objects.get(pk=product_id)
            egg_warehouse = Warehouse.objects.get(pk=warehouse_id)
            quantity = cls._decimal(
                StockService.actual_stock(
                    product=egg_product,
                    warehouse=egg_warehouse,
                )
            )
            unit_cost = cls._money(egg_product.standard_cost)
            value = cls._money(quantity * unit_cost)

            lines.append(
                {
                    "product": egg_product,
                    "product_id": egg_product.pk,
                    "warehouse": egg_warehouse,
                    "warehouse_id": egg_warehouse.pk,
                    "quantity": cls._quantity(quantity),
                    "unit_cost": unit_cost,
                    "inventory_value": value,
                }
            )
            total_quantity += quantity
            total_value += value

        return {
            "lines": lines,
            "total_quantity": cls._quantity(total_quantity),
            "total_inventory_value": cls._money(total_value),
        }

    @classmethod
    def incubation_valuation(
        cls,
        *,
        batch,
        egg_unit_cost,
        additional_incubation_cost=Decimal("0.00"),
    ):
        cls._saved(batch, IncubationBatch, "batch")

        egg_unit_cost = cls._money(egg_unit_cost)
        additional_cost = cls._money(additional_incubation_cost)
        if egg_unit_cost < 0 or additional_cost < 0:
            raise ValidationError(
                "Incubation valuation costs cannot be negative."
            )

        egg_input_value = cls._money(
            cls._decimal(batch.eggs_set) * egg_unit_cost
        )
        total_incubation_cost = cls._money(
            egg_input_value + additional_cost
        )
        cost_per_hatched_chick = (
            cls._money(
                total_incubation_cost
                / cls._decimal(batch.chicks_hatched)
            )
            if batch.chicks_hatched
            else Decimal("0.00")
        )
        loss_value = cls._money(
            cls._decimal(batch.unhatched_eggs) * egg_unit_cost
        )

        return {
            "batch": batch,
            "batch_id": batch.pk,
            "batch_code": batch.code,
            "eggs_set": batch.eggs_set,
            "egg_unit_cost": egg_unit_cost,
            "egg_input_value": egg_input_value,
            "additional_incubation_cost": additional_cost,
            "total_incubation_cost": total_incubation_cost,
            "chicks_hatched": batch.chicks_hatched,
            "unhatched_eggs": batch.unhatched_eggs,
            "unhatched_egg_loss_value": loss_value,
            "cost_per_hatched_chick": cost_per_hatched_chick,
            "hatchability_rate": batch.hatchability_rate,
        }

    @classmethod
    def portfolio_summary(
        cls,
        *,
        farm=None,
        start_date=None,
        end_date=None,
    ):
        flocks = PoultryFlock.objects.filter(
            status__in={"ACTIVE", "QUARANTINED"},
        ).select_related("farm", "house", "breed")
        if farm is not None:
            flocks = flocks.filter(farm=farm)

        flock_lines = [
            cls.flock_valuation(
                flock=flock,
                start_date=start_date,
                end_date=end_date,
            )
            for flock in flocks
        ]

        total_birds = sum(
            line["current_quantity"]
            for line in flock_lines
        )
        biological_asset_value = sum(
            (
                line["current_biological_asset_value"]
                for line in flock_lines
            ),
            Decimal("0"),
        )
        mortality_loss = sum(
            (line["mortality_loss"] for line in flock_lines),
            Decimal("0"),
        )
        feed_cost = sum(
            (line["feed_cost"] for line in flock_lines),
            Decimal("0"),
        )
        health_cost = sum(
            (line["health_cost"] for line in flock_lines),
            Decimal("0"),
        )

        egg_inventory = cls.egg_inventory_valuation(
            warehouse=(
                farm.warehouse
                if farm is not None and farm.warehouse_id
                else None
            )
        )

        total_valued_assets = cls._money(
            biological_asset_value
            + egg_inventory["total_inventory_value"]
        )

        return {
            "farm": farm,
            "flocks": flock_lines,
            "active_flock_count": len(flock_lines),
            "total_birds": total_birds,
            "biological_asset_value": cls._money(
                biological_asset_value
            ),
            "egg_inventory": egg_inventory,
            "egg_inventory_value": egg_inventory[
                "total_inventory_value"
            ],
            "total_valued_assets": total_valued_assets,
            "mortality_loss": cls._money(mortality_loss),
            "feed_cost": cls._money(feed_cost),
            "health_cost": cls._money(health_cost),
            "operating_cost": cls._money(feed_cost + health_cost),
            "start_date": start_date,
            "end_date": end_date,
            "valuation_method": "COST",
            "excludes_chick_inventory": True,
            "note": (
                "Chick inventory is excluded from the portfolio total to "
                "avoid double counting birds already assigned to flocks."
            ),
        }
