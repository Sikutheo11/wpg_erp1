from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from inventory.models import (
    Asset,
    Product,
    RawMaterial,
)

from ..models import (
    Counterparty,
    DebtLine,
    DebtRecord,
)


class DebtService:
    """
    Business logic for direct counterparty debts.

    A debt and all its product/service lines are committed
    together or rolled back together.
    """

    @staticmethod
    def _decimal(value, field_name):
        try:
            return Decimal(str(value))
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as error:
            raise ValidationError(
                {
                    field_name: (
                        "Enter a valid number."
                    )
                }
            ) from error

    @staticmethod
    def _actor(actor):
        if actor is None:
            return None

        if getattr(
            actor,
            "is_authenticated",
            False,
        ):
            return actor

        return getattr(actor, "user", None)

    @classmethod
    @transaction.atomic
    def create_debt(
        cls,
        *,
        counterparty,
        direction,
        lines,
        business_unit="GENERAL",
        transaction_date=None,
        due_date=None,
        notes="",
        actor=None,
    ):
        if not isinstance(
            counterparty,
            Counterparty,
        ) or not counterparty.pk:
            raise ValidationError(
                {
                    "counterparty": (
                        "Select a valid person or company."
                    )
                }
            )

        counterparty = (
            Counterparty.objects
            .select_for_update()
            .get(pk=counterparty.pk)
        )

        if not counterparty.is_active:
            raise ValidationError(
                {
                    "counterparty": (
                        "This person or company is inactive."
                    )
                }
            )

        valid_directions = {
            value
            for value, unused_label
            in DebtRecord.DIRECTIONS
        }
        if direction not in valid_directions:
            raise ValidationError(
                {
                    "direction": (
                        "Select who owes the money."
                    )
                }
            )

        valid_business_units = {
            value
            for value, unused_label
            in DebtRecord.BUSINESS_UNITS
        }
        if business_unit not in valid_business_units:
            raise ValidationError(
                {
                    "business_unit": (
                        "Select a valid business unit."
                    )
                }
            )

        lines = list(lines or [])
        if not lines:
            raise ValidationError(
                {
                    "lines": (
                        "Add at least one product or service."
                    )
                }
            )

        debt = DebtRecord(
            counterparty=counterparty,
            direction=direction,
            business_unit=business_unit,
            due_date=due_date,
            notes=(notes or "").strip(),
            status=DebtRecord.DRAFT,
            created_by=cls._actor(actor),
        )

        if transaction_date is not None:
            debt.transaction_date = transaction_date

        debt.full_clean()
        debt.save()

        valid_item_types = {
            value
            for value, unused_label
            in DebtLine.ITEM_TYPES
        }

        for position, line_data in enumerate(
            lines,
            start=1,
        ):
            if not isinstance(line_data, dict):
                raise ValidationError(
                    {
                        "lines": (
                            f"Line {position} contains "
                            "invalid information."
                        )
                    }
                )

            item_type = (
                line_data.get("item_type")
                or DebtLine.OTHER
            ).strip().upper()

            if item_type not in valid_item_types:
                raise ValidationError(
                    {
                        "lines": (
                            f"Line {position} has an "
                            "invalid item type."
                        )
                    }
                )

            product = line_data.get("product")
            raw_material = line_data.get(
                "raw_material"
            )
            asset = line_data.get("asset")

            if product is not None and (
                not isinstance(product, Product)
                or not product.pk
            ):
                raise ValidationError(
                    {
                        "lines": (
                            f"Line {position} has an "
                            "invalid product."
                        )
                    }
                )

            if raw_material is not None and (
                not isinstance(
                    raw_material,
                    RawMaterial,
                )
                or not raw_material.pk
            ):
                raise ValidationError(
                    {
                        "lines": (
                            f"Line {position} has an "
                            "invalid raw material."
                        )
                    }
                )

            if asset is not None and (
                not isinstance(asset, Asset)
                or not asset.pk
            ):
                raise ValidationError(
                    {
                        "lines": (
                            f"Line {position} has an "
                            "invalid asset."
                        )
                    }
                )

            quantity = cls._decimal(
                line_data.get("quantity", 1),
                "quantity",
            )
            unit_price = cls._decimal(
                line_data.get("unit_price"),
                "unit_price",
            )

            line = DebtLine(
                debt=debt,
                item_type=item_type,
                product=product,
                raw_material=raw_material,
                asset=asset,
                description=(
                    line_data.get("description")
                    or ""
                ).strip(),
                quantity=quantity,
                unit=(
                    line_data.get("unit")
                    or "piece"
                ).strip(),
                unit_price=unit_price,
            )

            try:
                line.full_clean()
            except ValidationError as error:
                raise ValidationError(
                    {
                        "lines": (
                            f"Line {position}: "
                            f"{'; '.join(error.messages)}"
                        )
                    }
                ) from error

            line.save()

        total = debt.recalculate_total()

        if total <= 0:
            raise ValidationError(
                {
                    "lines": (
                        "The debt total must be greater "
                        "than zero."
                    )
                }
            )

        debt.status = DebtRecord.OPEN
        debt.full_clean()
        debt.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        role_fields = []

        if (
            direction == DebtRecord.THEY_OWE_US
            and not counterparty.is_customer
        ):
            counterparty.is_customer = True
            role_fields.append("is_customer")

        if (
            direction == DebtRecord.WE_OWE_THEM
            and not counterparty.is_supplier
        ):
            counterparty.is_supplier = True
            role_fields.append("is_supplier")

        if role_fields:
            role_fields.append("updated_at")
            counterparty.save(
                update_fields=role_fields
            )

        return debt