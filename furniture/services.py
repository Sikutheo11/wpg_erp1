from decimal import Decimal
from django.core.exceptions import ValidationError

from .models import Order
from inventory.models import StockMovement


# =========================
# QUOTATION CALCULATION (AUTO BOM COST)
# =========================
def calculate_quotation(order):
    """
    Calculate total production cost based on BOM
    (ERP: auto quotation engine)
    """

    total = Decimal("0")

    # optimized query (avoid N+1)
    boms = order.product.boms.select_related("raw_material")

    for bom in boms:
        unit_cost = Decimal(bom.raw_material.unit_cost or 0)
        qty_per_unit = Decimal(bom.quantity_required or 0)

        total += qty_per_unit * unit_cost

    return total * Decimal(order.quantity_to_produce or 0)


# =========================
# STOCK DEDUCTION (SAFE ERP ENGINE)
# =========================
def deduct_stock(material, qty, user):
    """
    Deduct raw material stock safely (NO negative stock allowed)
    """

    qty = Decimal(qty)

    if qty <= 0:
        raise ValidationError("Quantity must be greater than 0")

    current_stock = Decimal(material.current_stock or 0)

    if current_stock < qty:
        raise ValidationError(
            f"Not enough stock for {material.name}. "
            f"Available: {current_stock}, Requested: {qty}"
        )

    return StockMovement.objects.create(
        raw_material=material,
        movement_type="OUT",
        quantity=qty,
        created_by=user
    )


# =========================
# ADD STOCK (IN MOVEMENT)
# =========================
def add_stock(material, qty, user, reference=""):
    """
    Add stock to inventory (Stock IN)
    """

    qty = Decimal(qty)

    if qty <= 0:
        raise ValidationError("Quantity must be greater than 0")

    return StockMovement.objects.create(
        raw_material=material,
        movement_type="IN",
        quantity=qty,
        reference_no=reference,
        created_by=user
    )