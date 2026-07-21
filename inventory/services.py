from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import StockMovement, Warehouse


class InventoryService:

    @staticmethod
    def stock_out(product, quantity, user, reference, warehouse=None):

        if warehouse is None:
            warehouse = Warehouse.objects.first()

        if warehouse is None:
            raise ValidationError(
                "No warehouse found. Please create a warehouse first."
            )

        StockMovement.objects.create(
            product=product,
            movement_type="OUT",
            quantity=Decimal(quantity),
            warehouse=warehouse,
            created_by=user,
            reference_no=reference,
        )