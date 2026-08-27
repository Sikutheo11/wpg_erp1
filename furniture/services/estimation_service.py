from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from furniture.models import BillOfMaterial, ProductionSettings
from furniture.planner_models import ProductionPlanMaterial


class ProductionPlanningCostService:
    """
    Pre-production estimate engine.

    Material prices come from Inventory and are snapshotted so historical
    quotations/plans do not silently change when current prices change.
    """

    ZERO = Decimal("0.00")
    HUNDRED = Decimal("100.00")

    @classmethod
    def money(cls, value):
        return Decimal(str(value or 0)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def quantity(cls, value):
        return Decimal(str(value or 0)).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def inventory_unit_cost(cls, raw_material):
        linked_product = getattr(raw_material, "linked_product", None)
        if linked_product is not None:
            standard_cost = Decimal(
                str(getattr(linked_product, "standard_cost", 0) or 0)
            )
            if standard_cost > 0:
                return cls.money(standard_cost)

        return cls.money(getattr(raw_material, "unit_cost", cls.ZERO))

    @classmethod
    @transaction.atomic
    def initialise_plan_defaults(cls, plan):
        settings = ProductionSettings.get_settings()
        changed = []

        if plan.default_wastage_rate == cls.ZERO:
            plan.default_wastage_rate = settings.wastage_rate
            changed.append("default_wastage_rate")
        if plan.overhead_rate == cls.ZERO:
            plan.overhead_rate = settings.overhead_rate
            changed.append("overhead_rate")
        if plan.target_profit_margin == cls.ZERO:
            plan.target_profit_margin = settings.target_profit_margin
            changed.append("target_profit_margin")

        if changed:
            plan.save(update_fields=changed + ["updated_at"])

        return plan

    @classmethod
    @transaction.atomic
    def sync_from_bom(cls, plan, replace=False):
        if not plan.product_id:
            raise ValidationError(
                "Select a product before importing its Bill of Materials."
            )

        boms = BillOfMaterial.objects.filter(
            product=plan.product
        ).select_related("raw_material")

        if not boms.exists():
            raise ValidationError(
                "This product has no Bill of Materials to import."
            )

        if replace:
            plan.materials.all().delete()

        created = 0
        updated = 0

        for bom in boms:
            _, was_created = ProductionPlanMaterial.objects.update_or_create(
                plan=plan,
                raw_material=bom.raw_material,
                defaults={"quantity_per_unit": bom.quantity_required},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return {"created": created, "updated": updated}

    @classmethod
    @transaction.atomic
    def calculate(cls, plan):
        if plan.quantity <= 0:
            raise ValidationError(
                "Production quantity must be greater than zero."
            )

        cls.initialise_plan_defaults(plan)
        material_total = cls.ZERO

        for line in plan.materials.select_related(
            "raw_material",
            "raw_material__linked_product",
        ):
            rate = (
                line.wastage_rate
                if line.wastage_rate is not None
                else plan.default_wastage_rate
            )
            rate = Decimal(str(rate or 0))
            if rate < 0:
                raise ValidationError(
                    f"Wastage cannot be negative for {line.raw_material}."
                )

            base_qty = (
                Decimal(str(line.quantity_per_unit))
                * Decimal(str(plan.quantity))
            )
            required_qty = (
                base_qty * (cls.HUNDRED + rate) / cls.HUNDRED
            )
            unit_cost = cls.inventory_unit_cost(line.raw_material)

            line.unit_cost_snapshot = unit_cost
            line.estimated_quantity = cls.quantity(required_qty)
            line.estimated_cost = cls.money(required_qty * unit_cost)
            line.save(
                update_fields=[
                    "unit_cost_snapshot",
                    "estimated_quantity",
                    "estimated_cost",
                ]
            )
            material_total += line.estimated_cost

        labour_total = cls.ZERO
        for line in plan.labour_lines.all():
            estimated_hours = (
                Decimal(str(line.hours_per_unit))
                * Decimal(str(plan.quantity))
            )
            line.estimated_hours = cls.quantity(estimated_hours)
            line.estimated_cost = cls.money(
                estimated_hours * Decimal(str(line.hourly_rate or 0))
            )
            line.save(
                update_fields=["estimated_hours", "estimated_cost"]
            )
            labour_total += line.estimated_cost

        machine_total = cls.ZERO
        for line in plan.machine_lines.all():
            estimated_hours = (
                Decimal(str(line.hours_per_unit))
                * Decimal(str(plan.quantity))
            )
            line.estimated_hours = cls.quantity(estimated_hours)
            line.estimated_cost = cls.money(
                estimated_hours * Decimal(str(line.hourly_cost or 0))
            )
            line.save(
                update_fields=["estimated_hours", "estimated_cost"]
            )
            machine_total += line.estimated_cost

        additional_total = sum(
            (
                cls.money(line.amount)
                for line in plan.additional_cost_lines.all()
            ),
            cls.ZERO,
        )

        material_total = cls.money(material_total)
        labour_total = cls.money(labour_total)
        machine_total = cls.money(machine_total)
        additional_total = cls.money(additional_total)

        direct_cost = cls.money(
            material_total + labour_total + machine_total
        )
        overhead_cost = cls.money(
            direct_cost
            * Decimal(str(plan.overhead_rate or 0))
            / cls.HUNDRED
        )
        total_cost = cls.money(
            direct_cost + overhead_cost + additional_total
        )
        cost_per_unit = cls.money(
            total_cost / Decimal(str(plan.quantity))
        )

        margin = Decimal(str(plan.target_profit_margin or 0))
        if margin < 0 or margin >= cls.HUNDRED:
            raise ValidationError(
                "Target gross margin must be at least 0 and below 100."
            )

        if margin:
            recommended_price = cls.money(
                total_cost
                / (Decimal("1.00") - margin / cls.HUNDRED)
            )
        else:
            recommended_price = total_cost

        expected_profit = cls.money(
            recommended_price - total_cost
        )

        plan.material_cost = material_total
        plan.labour_cost = labour_total
        plan.machine_cost = machine_total
        plan.additional_cost = additional_total
        plan.direct_cost = direct_cost
        plan.overhead_cost = overhead_cost
        plan.estimated_total_cost = total_cost
        plan.estimated_cost_per_unit = cost_per_unit
        plan.recommended_selling_price = recommended_price
        plan.expected_profit = expected_profit
        plan.status = "CALCULATED"
        plan.save(
            update_fields=[
                "material_cost",
                "labour_cost",
                "machine_cost",
                "additional_cost",
                "direct_cost",
                "overhead_cost",
                "estimated_total_cost",
                "estimated_cost_per_unit",
                "recommended_selling_price",
                "expected_profit",
                "status",
                "updated_at",
            ]
        )

        return {
            "quantity": plan.quantity,
            "material_cost": plan.material_cost,
            "labour_cost": plan.labour_cost,
            "machine_cost": plan.machine_cost,
            "additional_cost": plan.additional_cost,
            "direct_cost": plan.direct_cost,
            "overhead_cost": plan.overhead_cost,
            "estimated_total_cost": plan.estimated_total_cost,
            "estimated_cost_per_unit": plan.estimated_cost_per_unit,
            "recommended_selling_price": plan.recommended_selling_price,
            "expected_profit": plan.expected_profit,
        }
