from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from inventory.models import (
    Product,
    StockMovement,
    StockReservation,
    Warehouse,
)


class StockService:
    """
    Inventory stock calculation service.

    Stock is calculated from StockMovement records.

    V1 rules:
    - IN increases stock
    - OUT decreases stock
    - TRANSFER is ignored in global stock calculation
    - ADJUSTMENT is not included until adjustment direction is defined
    """

    ACTIVE_RESERVATION_STATUSES = {
        "RESERVED",
        "PARTIAL",
    }

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0))

    @classmethod
    def stock_in(
        cls,
        *,
        product,
        warehouse=None,
    ):
        queryset = StockMovement.objects.filter(
            product=product,
            movement_type="IN",
        )

        if warehouse is not None:
            queryset = queryset.filter(
                warehouse=warehouse,
            )

        return queryset.aggregate(
            total=Coalesce(
                Sum("quantity"),
                Value(
                    Decimal("0.00"),
                    output_field=DecimalField(
                        max_digits=18,
                        decimal_places=2,
                    ),
                ),
            )
        )["total"]

    @classmethod
    def stock_out(
        cls,
        *,
        product,
        warehouse=None,
    ):
        queryset = StockMovement.objects.filter(
            product=product,
            movement_type="OUT",
        )

        if warehouse is not None:
            queryset = queryset.filter(
                warehouse=warehouse,
            )

        return queryset.aggregate(
            total=Coalesce(
                Sum("quantity"),
                Value(
                    Decimal("0.00"),
                    output_field=DecimalField(
                        max_digits=18,
                        decimal_places=2,
                    ),
                ),
            )
        )["total"]

    @classmethod
    def actual_stock(
        cls,
        *,
        product,
        warehouse=None,
    ):
        """
        Physical stock currently recorded in the ledger.
        """

        if product is None:
            raise ValidationError(
                "Product is required."
            )

        stock_in = cls.stock_in(
            product=product,
            warehouse=warehouse,
        )

        stock_out = cls.stock_out(
            product=product,
            warehouse=warehouse,
        )

        return stock_in - stock_out

    @classmethod
    def reserved_stock(
        cls,
        *,
        product,
        warehouse=None,
    ):
        """
        Quantity already committed to active order reservations.
        """

        queryset = StockReservation.objects.filter(
            product=product,
            status__in=cls.ACTIVE_RESERVATION_STATUSES,
        )

        if warehouse is not None:
            queryset = queryset.filter(
                warehouse=warehouse,
            )

        return queryset.aggregate(
            total=Coalesce(
                Sum("reserved_quantity"),
                Value(
                    Decimal("0.00"),
                    output_field=DecimalField(
                        max_digits=18,
                        decimal_places=2,
                    ),
                ),
            )
        )["total"]

    @classmethod
    def available_stock(
        cls,
        *,
        product,
        warehouse=None,
    ):
        """
        Quantity available for new orders.
        """

        actual = cls.actual_stock(
            product=product,
            warehouse=warehouse,
        )

        reserved = cls.reserved_stock(
            product=product,
            warehouse=warehouse,
        )

        available = actual - reserved

        return max(
            available,
            Decimal("0.00"),
        )

    @classmethod
    def stock_summary(
        cls,
        *,
        product,
        warehouse=None,
    ):
        actual = cls.actual_stock(
            product=product,
            warehouse=warehouse,
        )

        reserved = cls.reserved_stock(
            product=product,
            warehouse=warehouse,
        )

        available = max(
            actual - reserved,
            Decimal("0.00"),
        )

        return {
            "product": product,
            "warehouse": warehouse,
            "actual_stock": actual,
            "reserved_stock": reserved,
            "available_stock": available,
            "reorder_level": cls._decimal(
                getattr(
                    product,
                    "reorder_level",
                    0,
                )
            ),
            "is_below_reorder_level": (
                available
                <= cls._decimal(
                    getattr(
                        product,
                        "reorder_level",
                        0,
                    )
                )
            ),
        }

    @classmethod
    def warehouse_stock_summary(
        cls,
        *,
        product,
    ):
        """
        Return stock summary for each warehouse.
        """

        summaries = []

        for warehouse in Warehouse.objects.all():
            summaries.append(
                cls.stock_summary(
                    product=product,
                    warehouse=warehouse,
                )
            )

        return summaries