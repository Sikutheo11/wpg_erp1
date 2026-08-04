from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from core.event_engine import EventEngine
from inventory.models import Product
from orders.models import Order, OrderItem

from ..models import (
    EcommerceCheckout,
    EcommerceCheckoutOrder,
    OnlineProduct,
)
from .marketplace_commission_service import (
    MarketplaceCommissionService,
)


class EcommerceCheckoutService:
    """
    Creates one customer checkout and one pending Enterprise Order per
    business unit represented in the cart.

    Checkout does not reserve or route stock. ReservationService and
    OrderRoutingService accept confirmed orders, so those actions belong to
    the later payment/order-confirmation workflow.
    """

    SUPPORTED_BUSINESS_UNITS = {
        "FURNITURE",
        "CONSTRUCTION",
        "AGRICULTURE",
    }

    @staticmethod
    def _authenticated_user(user):
        if user is not None and getattr(user, "is_authenticated", False):
            return user
        return None

    @staticmethod
    def _quantity(value):
        try:
            quantity = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                {"cart": "The cart contains an invalid quantity."}
            ) from error

        if quantity < 1:
            raise ValidationError(
                {"cart": "Cart quantities must be at least one."}
            )

        return quantity

    @staticmethod
    def _money(value, field_name):
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError(
                {field_name: "Enter a valid monetary amount."}
            ) from error

        if amount < Decimal("0.00"):
            raise ValidationError(
                {field_name: "The amount cannot be negative."}
            )

        return amount

    @staticmethod
    def _customer_value(customer_data, key, default=""):
        value = customer_data.get(key, default)
        if value is None:
            return default
        return str(value).strip()

    @classmethod
    def _validate_listing(cls, listing, quantity):
        product = listing.product

        if not product.is_active:
            raise ValidationError(
                {"cart": f"{product.name} is currently inactive."}
            )

        if not product.is_published:
            raise ValidationError(
                {"cart": f"{product.name} is no longer published."}
            )

        if listing.purchase_mode != OnlineProduct.ADD_TO_CART:
            raise ValidationError(
                {
                    "cart": (
                        f"{listing.display_title} requires a quotation "
                        "or made-to-order request."
                    )
                }
            )

        if product.business_unit not in cls.SUPPORTED_BUSINESS_UNITS:
            raise ValidationError(
                {
                    "cart": (
                        f"{product.name} belongs to an unsupported "
                        "Ecommerce business unit."
                    )
                }
            )

        if product.selling_price <= Decimal("0.00"):
            raise ValidationError(
                {
                    "cart": (
                        f"{product.name} does not have a valid selling price."
                    )
                }
            )

        if quantity < listing.minimum_order_quantity:
            raise ValidationError(
                {
                    "cart": (
                        f"{listing.display_title} has a minimum order "
                        f"quantity of {listing.minimum_order_quantity}."
                    )
                }
            )

        if (
            listing.maximum_order_quantity is not None
            and quantity > listing.maximum_order_quantity
        ):
            raise ValidationError(
                {
                    "cart": (
                        f"{listing.display_title} has a maximum order "
                        f"quantity of {listing.maximum_order_quantity}."
                    )
                }
            )

        if product.track_inventory and not product.allow_negative_stock:
            available = product.current_stock
            if Decimal(quantity) > available:
                raise ValidationError(
                    {
                        "cart": (
                            f"Only {available} {product.unit} of "
                            f"{product.name} is currently available."
                        )
                    }
                )

    @classmethod
    def _resolve_cart_items(cls, cart):
        raw_cart = getattr(cart, "cart", None)

        if not isinstance(raw_cart, dict) or not raw_cart:
            raise ValidationError({"cart": "Your cart is empty."})

        quantities = {}
        listing_ids = []

        for raw_id, stored in raw_cart.items():
            try:
                listing_id = int(raw_id)
            except (TypeError, ValueError) as error:
                raise ValidationError(
                    {"cart": "The cart contains an invalid product."}
                ) from error

            if not isinstance(stored, dict):
                raise ValidationError(
                    {"cart": "The cart contains invalid product data."}
                )

            listing_ids.append(listing_id)
            quantities[listing_id] = cls._quantity(stored.get("quantity", 1))

        listings = list(
            OnlineProduct.objects.select_related(
                "product",
                "product__category",
            )
            .filter(pk__in=listing_ids)
            .order_by("pk")
        )

        if len(listings) != len(set(listing_ids)):
            raise ValidationError(
                {"cart": "One or more online products no longer exist."}
            )

        # Product rows are the authoritative price and availability records.
        # Lock them before the final checkout validation.
        product_ids = [listing.product_id for listing in listings]
        locked_products = {
            product.pk: product
            for product in (
                Product.objects.select_for_update()
                .filter(pk__in=product_ids)
                .order_by("pk")
            )
        }

        resolved_items = []

        for listing in listings:
            product = locked_products.get(listing.product_id)
            if product is None:
                raise ValidationError(
                    {"cart": "An Inventory product no longer exists."}
                )

            # Use the locked authoritative Product instance.
            listing.product = product
            quantity = quantities[listing.pk]
            cls._validate_listing(listing, quantity)

            resolved_items.append(
                {
                    "online_product": listing,
                    "product": product,
                    "business_unit": product.business_unit,
                    "quantity": quantity,
                    "unit_price": product.selling_price,
                    "subtotal": product.selling_price * quantity,
                }
            )

        return resolved_items

    @classmethod
    @transaction.atomic
    def create_checkout(
        cls,
        *,
        cart,
        customer_data,
        user=None,
        actor=None,
        discount=Decimal("0.00"),
        tax=Decimal("0.00"),
    ):
        if not hasattr(customer_data, "get"):
            raise ValidationError(
                {"customer": "Valid checkout customer data is required."}
            )

        customer_name = cls._customer_value(customer_data, "full_name")
        customer_phone = cls._customer_value(customer_data, "phone")

        if not customer_name:
            raise ValidationError({"full_name": "Customer name is required."})

        if not customer_phone:
            raise ValidationError({"phone": "Customer phone is required."})

        items = cls._resolve_cart_items(cart)
        grouped_items = defaultdict(list)

        for item in items:
            grouped_items[item["business_unit"]].append(item)

        subtotal = sum(
            (item["subtotal"] for item in items),
            Decimal("0.00"),
        )
        discount = cls._money(discount, "discount")
        tax = cls._money(tax, "tax")

        if discount > subtotal:
            raise ValidationError(
                {"discount": "Discount cannot exceed the checkout subtotal."}
            )

        authenticated_user = cls._authenticated_user(user)
        event_actor = cls._authenticated_user(actor) or authenticated_user

        checkout = EcommerceCheckout(
            user=authenticated_user,
            status="PENDING",
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=cls._customer_value(customer_data, "email"),
            province=cls._customer_value(customer_data, "province"),
            district=cls._customer_value(customer_data, "district"),
            sector=cls._customer_value(customer_data, "sector"),
            cell=cls._customer_value(customer_data, "cell"),
            village=cls._customer_value(customer_data, "village"),
            delivery_address=cls._customer_value(
                customer_data,
                "delivery_address",
            ),
            notes=cls._customer_value(customer_data, "notes"),
            subtotal=subtotal,
            discount=discount,
            tax=tax,
        )
        checkout.full_clean()
        checkout.save()

        orders = []

        ordered_business_units = sorted(grouped_items)
        remaining_discount = discount
        remaining_tax = tax

        for index, business_unit in enumerate(ordered_business_units):
            unit_items = grouped_items[business_unit]
            unit_subtotal = sum(
                (item["subtotal"] for item in unit_items),
                Decimal("0.00"),
            )

            is_last_group = index == len(ordered_business_units) - 1
            if is_last_group:
                unit_discount = remaining_discount
                unit_tax = remaining_tax
            else:
                unit_ratio = unit_subtotal / subtotal
                unit_discount = (
                    discount * unit_ratio
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
                unit_tax = (
                    tax * unit_ratio
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
                remaining_discount -= unit_discount
                remaining_tax -= unit_tax

            order = Order(
                user=authenticated_user,
                business_unit=business_unit,
                order_type="ECOMMERCE",
                status="PENDING",
                payment_status="UNPAID",
                delivery_status="NOT_STARTED",
                customer_name=checkout.customer_name,
                customer_phone=checkout.customer_phone,
                customer_email=checkout.customer_email or None,
                province=checkout.province,
                district=checkout.district,
                sector=checkout.sector,
                cell=checkout.cell,
                village=checkout.village,
                delivery_address=checkout.delivery_address,
                notes=checkout.notes,
                subtotal=unit_subtotal,
                discount=unit_discount,
                tax=unit_tax,
            )
            order.full_clean()
            order.save()

            order_items = []
            for item in unit_items:
                order_item = OrderItem(
                    order=order,
                    product=item["product"],
                    product_name=item["online_product"].display_title,
                    quantity=item["quantity"],
                    price=item["unit_price"],
                    specifications="",
                )
                order_item.full_clean()
                order_items.append(order_item)

            OrderItem.objects.bulk_create(order_items)

            for order_item, item in zip(
                order_items,
                unit_items,
                strict=True,
            ):
                MarketplaceCommissionService.create_order_line(
                    order_item=order_item,
                    online_product=item["online_product"],
                )

            checkout_order = EcommerceCheckoutOrder(
                checkout=checkout,
                order=order,
                business_unit=business_unit,
                amount=order.total_amount,
            )
            checkout_order.full_clean()
            checkout_order.save()
            orders.append(order)

        checkout.status = "ORDERED"
        checkout.save(update_fields=[
            "status",
            "total_amount",
            "updated_at",
        ])

        order_metadata = [
            {
                "order_id": order.pk,
                "order_number": order.order_number,
                "business_unit": order.business_unit,
                "total_amount": str(order.total_amount),
            }
            for order in orders
        ]

        # Clear the session cart only after the database commit succeeds.
        transaction.on_commit(cart.clear)

        transaction.on_commit(
            lambda: EventEngine.dispatch(
                event_code="ECOMMERCE_CHECKOUT_CREATED",
                actor=event_actor,
                obj=checkout,
                title="Ecommerce Checkout Created",
                message=(
                    f"Checkout {checkout.checkout_number} created "
                    f"{len(orders)} enterprise order(s)."
                ),
                level="INFO",
                metadata={
                    "checkout_id": checkout.pk,
                    "checkout_number": checkout.checkout_number,
                    "customer_name": checkout.customer_name,
                    "subtotal": str(checkout.subtotal),
                    "discount": str(checkout.discount),
                    "tax": str(checkout.tax),
                    "total_amount": str(checkout.total_amount),
                    "orders": order_metadata,
                },
                notify_groups=["Order Manager"],
                notify_owner=True,
            )
        )

        return {
            "checkout": checkout,
            "orders": orders,
            "grouped_items": dict(grouped_items),
        }
