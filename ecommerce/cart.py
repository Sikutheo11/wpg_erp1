from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from .models import OnlineProduct


class Cart:
    """
    Session-backed Ecommerce cart.

    Session keys are OnlineProduct primary keys. Inventory Product identity,
    business unit, price and stock are always refreshed from the database
    before display and again during checkout.
    """

    SESSION_KEY = "cart"

    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(self.SESSION_KEY)

        if not isinstance(self.cart, dict):
            self.cart = {}
            self.session[self.SESSION_KEY] = self.cart

    @staticmethod
    def _as_quantity(value):
        try:
            quantity = int(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                {"quantity": "Enter a valid whole-number quantity."}
            ) from error

        if quantity < 1:
            raise ValidationError(
                {"quantity": "Quantity must be at least one."}
            )

        return quantity

    @staticmethod
    def _as_decimal(value):
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError("The cart contains an invalid price.") from error

    @staticmethod
    def _available_stock(product):
        if not product.track_inventory or product.allow_negative_stock:
            return None

        return product.current_stock

    @classmethod
    def _validate_quantity(cls, listing, quantity):
        if quantity < listing.minimum_order_quantity:
            raise ValidationError(
                {
                    "quantity": (
                        f"Minimum order quantity is "
                        f"{listing.minimum_order_quantity}."
                    )
                }
            )

        if (
            listing.maximum_order_quantity is not None
            and quantity > listing.maximum_order_quantity
        ):
            raise ValidationError(
                {
                    "quantity": (
                        f"Maximum order quantity is "
                        f"{listing.maximum_order_quantity}."
                    )
                }
            )

        available = cls._available_stock(listing.product)
        if available is not None and Decimal(quantity) > available:
            raise ValidationError(
                {
                    "quantity": (
                        f"Only {available} {listing.product.unit} "
                        "is currently available."
                    )
                }
            )

    @staticmethod
    def _listing_queryset():
        return OnlineProduct.objects.select_related(
            "product",
            "product__category",
        )

    @classmethod
    def _get_cart_listing(cls, online_product_id):
        try:
            listing = cls._listing_queryset().get(pk=online_product_id)
        except OnlineProduct.DoesNotExist as error:
            raise ValidationError("This online product no longer exists.") from error

        if not listing.product.is_active:
            raise ValidationError("This product is currently inactive.")

        if not listing.product.is_published:
            raise ValidationError("This product is not currently published.")

        if listing.purchase_mode != OnlineProduct.ADD_TO_CART:
            raise ValidationError(
                "This product requires a quotation or made-to-order request."
            )

        if listing.product.selling_price <= Decimal("0.00"):
            raise ValidationError(
                "This product does not yet have a valid online selling price."
            )

        return listing

    def add(self, online_product_id, quantity=1, *, replace=False):
        listing = self._get_cart_listing(online_product_id)
        quantity = self._as_quantity(quantity)
        key = str(listing.pk)

        existing_quantity = 0
        if key in self.cart and not replace:
            existing_quantity = self._as_quantity(
                self.cart[key].get("quantity", 1)
            )

        final_quantity = quantity if replace else existing_quantity + quantity
        self._validate_quantity(listing, final_quantity)

        self.cart[key] = {
            "online_product_id": listing.pk,
            "product_id": listing.product_id,
            "quantity": final_quantity,
            "unit_price": str(listing.product.selling_price),
            # Temporary compatibility key for the legacy cart/checkout views.
            # Remove after those views are replaced by Cart.items().
            "price": str(listing.product.selling_price),
        }
        self.save()

    def update(self, online_product_id, quantity):
        key = str(online_product_id)

        try:
            parsed_quantity = int(quantity)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                {"quantity": "Enter a valid whole-number quantity."}
            ) from error

        if parsed_quantity <= 0:
            self.remove(online_product_id)
            return

        self.add(
            online_product_id,
            parsed_quantity,
            replace=True,
        )

    def remove(self, online_product_id):
        key = str(online_product_id)

        if key in self.cart:
            del self.cart[key]
            self.save()

    def clear(self):
        self.cart = {}
        self.session[self.SESSION_KEY] = self.cart
        self.save()

    def save(self):
        self.session[self.SESSION_KEY] = self.cart
        self.session.modified = True

    def items(self):
        if not self.cart:
            return []

        valid_ids = []
        for key in self.cart:
            try:
                valid_ids.append(int(key))
            except (TypeError, ValueError):
                continue

        listings = {
            listing.pk: listing
            for listing in self._listing_queryset().filter(pk__in=valid_ids)
        }

        resolved_items = []
        stale_keys = []

        for key, stored in self.cart.items():
            try:
                listing_id = int(key)
                listing = listings[listing_id]
                quantity = self._as_quantity(stored.get("quantity", 1))
            except (KeyError, TypeError, ValueError, ValidationError):
                stale_keys.append(key)
                continue

            current_price = listing.product.selling_price
            subtotal = current_price * quantity

            resolved_items.append(
                {
                    "online_product": listing,
                    "product": listing.product,
                    "business_unit": listing.product.business_unit,
                    "quantity": quantity,
                    "unit_price": current_price,
                    "subtotal": subtotal,
                }
            )

        if stale_keys:
            for key in stale_keys:
                self.cart.pop(key, None)
            self.save()

        return resolved_items

    def grouped_items(self):
        groups = defaultdict(list)

        for item in self.items():
            groups[item["business_unit"]].append(item)

        return dict(groups)

    @property
    def total(self):
        return sum(
            (item["subtotal"] for item in self.items()),
            Decimal("0.00"),
        )

    @property
    def count(self):
        return sum(item["quantity"] for item in self.items())

    def __len__(self):
        return self.count

    def __bool__(self):
        return bool(self.cart)
