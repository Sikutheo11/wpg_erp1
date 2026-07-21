from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from inventory.models import StockMovement, Warehouse


# =========================
# QUOTATION CALCULATION
# =========================

def calculate_quotation(order):
    total = Decimal("0")

    boms = order.product.boms.select_related(
        "raw_material"
    )

    for bom in boms:
        unit_cost = Decimal(
            bom.raw_material.unit_cost or 0
        )

        qty_per_unit = Decimal(
            bom.quantity_required or 0
        )

        total += qty_per_unit * unit_cost

    return total * Decimal(
        order.quantity_to_produce or 0
    )


# =========================
# RAW MATERIAL STOCK OUT
# =========================

def deduct_stock(material, qty, user):
    qty = Decimal(qty)

    if qty <= 0:
        raise ValidationError(
            "Quantity must be greater than 0"
        )

    current_stock = Decimal(
        material.current_stock or 0
    )

    if current_stock < qty:
        raise ValidationError(
            f"Not enough stock for {material.name}. "
            f"Available: {current_stock}, Requested: {qty}"
        )

    return StockMovement.objects.create(
        raw_material=material,
        movement_type="OUT",
        quantity=qty,
        created_by=user,
    )


# =========================
# RAW MATERIAL STOCK IN
# =========================

def add_stock(material, qty, user, reference=""):
    qty = Decimal(qty)

    if qty <= 0:
        raise ValidationError(
            "Quantity must be greater than 0"
        )

    return StockMovement.objects.create(
        raw_material=material,
        movement_type="IN",
        quantity=qty,
        reference_no=reference,
        created_by=user,
    )


# =========================
# PRODUCTION SERVICE
# =========================

class ProductionService:

    @staticmethod
    @transaction.atomic
    def complete_job(production_job, form, user):

        output = form.save(commit=False)

        output.production_job = production_job
        output.produced_by = user.employee
        output.save()

        warehouse = Warehouse.objects.first()

        if warehouse is None:
            raise ValidationError(
                "No warehouse found. Please create a warehouse first."
            )

        StockMovement.objects.create(
            product=output.product,
            movement_type="IN",
            quantity=output.quantity_produced,
            warehouse=warehouse,
            created_by=user,
            reference_no=f"PRODUCTION-JOB-{production_job.id}",
        )

        production_job.status = "COMPLETED"
        production_job.save()

        if production_job.order:
            production_job.order.status = "COMPLETED"
            production_job.order.save()

        return output


# =========================
# PRODUCTION COST ENGINE
# =========================

class ProductionCostService:

    @staticmethod
    def material_cost(production_job):
        return sum(
            item.total_cost
            for item in production_job.materials.all()
        )

    @staticmethod
    def labour_cost(production_job):
        return sum(
            item.total_cost
            for item in production_job.labours.all()
        )

    @staticmethod
    def machine_cost(production_job):
        return sum(
            item.total_cost
            for item in production_job.machines.all()
        )

    @staticmethod
    def output_quantity(production_job):
        return sum(
            item.quantity_produced or 0
            for item in production_job.outputs.all()
        )

    @staticmethod
    def total_cost(production_job):
        return (
            ProductionCostService.material_cost(production_job)
            + ProductionCostService.labour_cost(production_job)
            + ProductionCostService.machine_cost(production_job)
        )

    @staticmethod
    def cost_per_unit(production_job):
        quantity = ProductionCostService.output_quantity(
            production_job
        )

        if quantity <= 0:
            return 0

        return (
            ProductionCostService.total_cost(production_job)
            / quantity
        )

    @staticmethod
    def profit_per_unit(production_job):
        if not production_job.product:
            return 0

        selling_price = (
            production_job.product.selling_price or 0
        )

        return (
            selling_price
            - ProductionCostService.cost_per_unit(production_job)
        )

    @staticmethod
    def expected_profit(production_job):
        quantity = ProductionCostService.output_quantity(
            production_job
        )

        return (
            ProductionCostService.profit_per_unit(production_job)
            * quantity
        )

    @staticmethod
    def summary(production_job):
        return {
            "material_cost": ProductionCostService.material_cost(production_job),
            "labour_cost": ProductionCostService.labour_cost(production_job),
            "machine_cost": ProductionCostService.machine_cost(production_job),
            "total_cost": ProductionCostService.total_cost(production_job),
            "output_quantity": ProductionCostService.output_quantity(production_job),
            "cost_per_unit": ProductionCostService.cost_per_unit(production_job),
            "profit_per_unit": ProductionCostService.profit_per_unit(production_job),
            "expected_profit": ProductionCostService.expected_profit(production_job),
        }