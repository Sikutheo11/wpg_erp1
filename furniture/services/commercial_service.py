from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from sales.models import Customer
from sales.services import QuotationService


class CustomFurnitureQuotationService:
    """
    Thin integration bridge only.

    Ownership:
      - Furniture ProductionPlan owns technical estimate/cost.
      - Sales QuotationService owns quotation items, pricing and totals.
      - Orders owns the customer request/workflow.

    Do not duplicate quotation calculations here.
    """

    ALLOWED_PLAN_STATUSES = {"CALCULATED", "APPROVED"}

    @classmethod
    def _customer_for_order(cls, order):
        customer = None

        if order.user_id:
            customer = Customer.objects.filter(user=order.user).first()

        if customer is None and order.customer_email:
            customer = Customer.objects.filter(
                email__iexact=order.customer_email
            ).first()

        if customer is None and order.customer_phone:
            customer = Customer.objects.filter(
                phone=order.customer_phone
            ).first()

        if customer is None:
            customer = Customer.objects.create(
                user=(
                    order.user
                    if order.user_id
                    and not Customer.objects.filter(user=order.user).exists()
                    else None
                ),
                full_name=order.customer_name or "Furniture Customer",
                phone=order.customer_phone,
                email=order.customer_email or "",
                address=order.delivery_address or "",
            )

        return customer

    @classmethod
    def _validate_order(cls, order):
        if order.business_unit != "FURNITURE":
            raise ValidationError(
                "Only Furniture orders can use Furniture Production Planner quotations."
            )

        if order.order_type != "CUSTOM_FURNITURE":
            raise ValidationError(
                "Customer quotation generation is limited to Custom Furniture orders."
            )

        plans = list(
            order.furniture_production_plans
            .select_related("product", "sales_quotation_item")
            .order_by("pk")
        )

        if not plans:
            raise ValidationError(
                "Add at least one production plan before preparing a quotation."
            )

        invalid = [
            plan.name
            for plan in plans
            if plan.status not in cls.ALLOWED_PLAN_STATUSES
            or plan.estimated_total_cost <= 0
            or plan.recommended_selling_price <= 0
        ]

        if invalid:
            raise ValidationError(
                "Calculate and review these production plans first: "
                + ", ".join(invalid)
            )

        return plans

    @classmethod
    @transaction.atomic
    def sync_order_quotation(
        cls,
        order,
        actor=None,
        valid_until=None,
        discount=Decimal("0.00"),
        tax=Decimal("0.00"),
        notes="",
    ):
        plans = cls._validate_order(order)

        discount = Decimal(str(discount or 0))
        tax = Decimal(str(tax or 0))

        if discount < 0 or tax < 0:
            raise ValidationError("Discount and tax cannot be negative.")

        valid_until = (
            valid_until
            or timezone.localdate() + timedelta(days=30)
        )

        customer = cls._customer_for_order(order)
        quotation = getattr(order, "customer_quotation", None)

        if quotation is None:
            # Important: SalesQuotation validates immediately on creation.
            # At this point subtotal is zero, therefore commercial discount
            # and tax are applied only AFTER all planner items are present.
            quotation = QuotationService.create_quotation(
                customer=customer,
                business_unit="FURNITURE",
                order_type="CUSTOM_FURNITURE",
                valid_until=valid_until,
                discount=Decimal("0.00"),
                tax=Decimal("0.00"),
                notes=notes or (
                    f"Prepared from customer request {order.order_number}."
                ),
                actor=actor,
            )
            order.customer_quotation = quotation
        else:
            if quotation.status not in QuotationService.EDITABLE_STATUSES:
                raise ValidationError(
                    "Only a draft or rejected customer quotation can be refreshed."
                )
            if quotation.converted_order_id:
                raise ValidationError(
                    "A converted quotation cannot be refreshed."
                )

            quotation.customer = customer
            quotation.business_unit = "FURNITURE"
            quotation.order_type = "CUSTOM_FURNITURE"
            quotation.valid_until = valid_until
            if notes:
                quotation.notes = notes.strip()

            # Keep pricing valid while planner lines are synchronized.
            quotation.discount = Decimal("0.00")
            quotation.tax = Decimal("0.00")
            quotation.status = "draft"
            # Sales QuotationService owns monetary validation and recalculation.
            # Avoid validating stale calculated totals before that recalculation.
            quotation.save(
                update_fields=[
                    "customer",
                    "business_unit",
                    "order_type",
                    "valid_until",
                    "notes",
                    "discount",
                    "tax",
                    "status",
                    "updated_at",
                ]
            )

        active_item_ids = set()

        for plan in plans:
            product_name = (
                getattr(plan.product, "name", "")
                if plan.product_id
                else plan.name
            )
            unit_price = plan.recommended_unit_price
            item = plan.sales_quotation_item

            if item is None:
                item = QuotationService.add_item(
                    quotation=quotation,
                    product=plan.product,
                    product_name=product_name,
                    specifications=plan.assumptions or "",
                    quantity=plan.quantity,
                    unit_price=unit_price,
                    actor=actor,
                )
                plan.sales_quotation_item = item
                plan.save(
                    update_fields=[
                        "sales_quotation_item",
                        "updated_at",
                    ]
                )
            else:
                if item.quotation_id != quotation.pk:
                    raise ValidationError(
                        f"{plan.name} is already linked to another quotation."
                    )

                # Use the shared Sales engine rather than saving quotation
                # items directly from Furniture.
                item = QuotationService.update_item(
                    item=item,
                    product=plan.product,
                    product_name=product_name,
                    specifications=plan.assumptions or "",
                    quantity=plan.quantity,
                    unit_price=unit_price,
                    actor=actor,
                )

            active_item_ids.add(item.pk)

        # A quotation created by this bridge should not retain planner-linked
        # items whose production plans are no longer part of this order.
        stale_items = list(
            quotation.items.filter(
                source_production_plan__isnull=False
            ).exclude(pk__in=active_item_ids)
        )
        for item in stale_items:
            QuotationService.remove_item(
                item=item,
                actor=actor,
            )

        # Sales owns discount/tax validation and the final quotation total.
        quotation = QuotationService.update_pricing(
            quotation=quotation,
            discount=discount,
            tax=tax,
            actor=actor,
        )

        order.subtotal = quotation.subtotal
        order.discount = quotation.discount
        order.tax = quotation.tax
        order.status = "AWAITING_CUSTOMER_APPROVAL"
        order.save(
            update_fields=[
                "customer_quotation",
                "subtotal",
                "discount",
                "tax",
                "status",
                "updated_at",
                "total_amount",
            ]
        )

        return quotation
