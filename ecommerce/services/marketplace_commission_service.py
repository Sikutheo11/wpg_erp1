from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ecommerce.models import (
    MarketplaceOrderLine,
    SellerProductAssignment,
)
from orders.models import OrderItem


class MarketplaceCommissionService:
    """Creates immutable seller and commission snapshots for Ecommerce items."""

    MONEY = Decimal("0.01")
    HUNDRED = Decimal("100.00")
    ZERO = Decimal("0.00")

    @classmethod
    def _money(cls, value):
        return Decimal(str(value or 0)).quantize(
            cls.MONEY,
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def _assignment(cls, *, online_product):
        assignment = (
            SellerProductAssignment.objects
            .select_related(
                "seller",
                "seller__poultry_farm",
                "online_product",
                "online_product__product",
            )
            .filter(
                online_product=online_product,
                is_active=True,
                seller__is_active=True,
                effective_from__lte=timezone.localdate(),
            )
            .first()
        )

        if assignment is None:
            raise ValidationError(
                (
                    f"Online product {online_product.display_title} "
                    "does not have an active Marketplace seller assignment."
                )
            )

        if (
            online_product.product.business_unit == "AGRICULTURE"
            and assignment.seller.poultry_farm_id is None
        ):
            raise ValidationError(
                (
                    f"Agriculture product {online_product.display_title} "
                    "must be assigned to a seller linked to a poultry farm."
                )
            )

        return assignment

    @classmethod
    def calculate_amounts(
        cls,
        *,
        quantity,
        unit_price,
        commission_rate,
    ):
        quantity = Decimal(str(quantity))
        unit_price = cls._money(unit_price)
        commission_rate = Decimal(str(commission_rate or 0)).quantize(
            cls.MONEY,
            rounding=ROUND_HALF_UP,
        )

        if quantity <= 0:
            raise ValidationError("Marketplace quantity must be greater than zero.")
        if unit_price < cls.ZERO:
            raise ValidationError("Marketplace unit price cannot be negative.")
        if commission_rate < cls.ZERO or commission_rate > cls.HUNDRED:
            raise ValidationError("Commission rate must be between 0 and 100.")

        gross_amount = cls._money(quantity * unit_price)
        commission_amount = cls._money(
            gross_amount * commission_rate / cls.HUNDRED
        )
        seller_net_amount = cls._money(
            gross_amount - commission_amount
        )

        return {
            "quantity": quantity,
            "unit_price": unit_price,
            "gross_amount": gross_amount,
            "commission_rate": commission_rate,
            "commission_amount": commission_amount,
            "seller_net_amount": seller_net_amount,
        }

    @classmethod
    @transaction.atomic
    def create_order_line(
        cls,
        *,
        order_item,
        online_product,
    ):
        if not isinstance(order_item, OrderItem) or order_item.pk is None:
            raise ValidationError("A saved OrderItem is required.")

        if order_item.order.order_type != "ECOMMERCE":
            raise ValidationError(
                "Marketplace commission snapshots require an Ecommerce order."
            )

        if online_product.product_id != order_item.product_id:
            raise ValidationError(
                "Online product does not match the OrderItem product."
            )

        existing = MarketplaceOrderLine.objects.filter(
            order_item=order_item
        ).first()
        if existing is not None:
            return existing, False

        assignment = cls._assignment(
            online_product=online_product,
        )
        seller = assignment.seller
        amounts = cls.calculate_amounts(
            quantity=order_item.quantity,
            unit_price=order_item.price,
            commission_rate=assignment.effective_commission_rate,
        )

        marketplace_line = MarketplaceOrderLine(
            order_item=order_item,
            online_product=online_product,
            seller=seller,
            farm=seller.poultry_farm,
            seller_code=seller.code,
            seller_name=seller.name,
            product_name=order_item.product_name,
            quantity=amounts["quantity"],
            unit_price=amounts["unit_price"],
            gross_amount=amounts["gross_amount"],
            commission_rate=amounts["commission_rate"],
            commission_amount=amounts["commission_amount"],
            seller_net_amount=amounts["seller_net_amount"],
        )
        marketplace_line.full_clean()
        marketplace_line.save()

        return marketplace_line, True

    @classmethod
    @transaction.atomic
    def create_for_order(
        cls,
        *,
        order,
        online_products_by_product_id,
    ):
        results = []

        for order_item in order.items.select_related("product").order_by("pk"):
            online_product = online_products_by_product_id.get(
                order_item.product_id
            )
            if online_product is None:
                raise ValidationError(
                    (
                        f"No OnlineProduct was supplied for order item "
                        f"{order_item.product_name}."
                    )
                )

            marketplace_line, created = cls.create_order_line(
                order_item=order_item,
                online_product=online_product,
            )
            results.append(
                {
                    "marketplace_line": marketplace_line,
                    "created": created,
                }
            )

        return results
