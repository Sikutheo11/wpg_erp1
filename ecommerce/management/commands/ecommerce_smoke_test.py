from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.test import Client, override_settings
from django.urls import reverse

from ecommerce.models import OnlineProduct


class Command(BaseCommand):
    help = (
        "Run non-destructive Ecommerce catalogue and cart smoke tests "
        "against the current database."
    )

    def _check_response(self, label, response, expected_status=200):
        if response.status_code != expected_status:
            raise CommandError(
                f"{label} failed: expected HTTP {expected_status}, "
                f"received HTTP {response.status_code}."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"PASS  {label} ({response.status_code})"
            )
        )

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
    def handle(self, *args, **options):
        client = Client()

        self._check_response(
            "Shop page",
            client.get(reverse("ecommerce:shop")),
        )
        self._check_response(
            "Empty cart page",
            client.get(reverse("ecommerce:cart_detail")),
        )

        listing = (
            OnlineProduct.objects
            .select_related("product")
            .filter(
                purchase_mode=OnlineProduct.ADD_TO_CART,
                product__business_unit__in={
                    "FURNITURE",
                    "CONSTRUCTION",
                    "AGRICULTURE",
                },
                product__is_active=True,
                product__is_published=True,
                product__selling_price__gt=Decimal("0.00"),
            )
            .order_by("product__business_unit", "pk")
            .first()
        )

        if listing is None:
            self.stdout.write(
                self.style.WARNING(
                    "SKIP  Product detail and cart-add tests: no eligible "
                    "ADD_TO_CART product was found."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "Create or publish an OnlineProduct with a positive "
                    "selling price, then run this command again."
                )
            )
            return

        self._check_response(
            f"Product detail: {listing.display_title}",
            client.get(
                reverse(
                    "ecommerce:product_detail",
                    kwargs={"slug": listing.slug},
                )
            ),
        )

        add_response = client.post(
            reverse(
                "ecommerce:add_to_cart",
                kwargs={"product_id": listing.pk},
            ),
            {
                "quantity": listing.minimum_order_quantity,
            },
        )
        self._check_response(
            f"Add to cart: {listing.display_title}",
            add_response,
            expected_status=302,
        )

        cart_response = client.get(reverse("ecommerce:cart_detail"))
        self._check_response("Populated cart page", cart_response)

        session_cart = client.session.get("cart", {})
        stored_item = session_cart.get(str(listing.pk))
        expected_quantity = listing.minimum_order_quantity

        if (
            not stored_item
            or int(stored_item.get("quantity", 0)) != expected_quantity
        ):
            raise CommandError(
                "Cart session validation failed after adding the product."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"PASS  Cart session quantity ({expected_quantity})"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Ecommerce catalogue and cart smoke tests passed."
            )
        )
