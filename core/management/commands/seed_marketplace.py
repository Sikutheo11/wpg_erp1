from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Feature, RoleFeature


FEATURES = (
    {
        "code": "MARKETPLACE_DASHBOARD",
        "name": "Marketplace Dashboard",
        "url_name": "ecommerce:ecommerce_dashboard",
        "icon": "fas fa-store",
        "order": 10,
    },
    {
        "code": "MARKETPLACE_SHOP",
        "name": "Shop",
        "url_name": "ecommerce:shop",
        "icon": "fas fa-shopping-bag",
        "order": 20,
    },
    {
        "code": "MARKETPLACE_PRODUCTS",
        "name": "Online Products",
        "url_name": "ecommerce:online_product_list",
        "icon": "fas fa-box-open",
        "order": 30,
    },
    {
        "code": "MARKETPLACE_ORDERS",
        "name": "Online Orders",
        "url_name": "ecommerce:my_orders",
        "icon": "fas fa-receipt",
        "order": 40,
    },
    {
        "code": "MARKETPLACE_SELLERS",
        "name": "Marketplace Sellers",
        "url_name": "ecommerce:marketplace_seller_list",
        "icon": "fas fa-store-alt",
        "order": 50,
    },
    {
        "code": "MARKETPLACE_COMMISSIONS",
        "name": "Product Commissions",
        "url_name": "ecommerce:online_product_list",
        "icon": "fas fa-percent",
        "order": 60,
    },
    {
        "code": "MARKETPLACE_SETTLEMENTS",
        "name": "Seller Settlements",
        "url_name": "ecommerce:seller_settlement_list",
        "icon": "fas fa-file-invoice-dollar",
        "order": 70,
    },
    {
        "code": "MARKETPLACE_PAYMENTS",
        "name": "Marketplace Payments",
        "url_name": "ecommerce:payment_list",
        "icon": "fas fa-money-check-alt",
        "order": 80,
    },
    {
        "code": "MARKETPLACE_REPORTS",
        "name": "Marketplace Reports",
        "url_name": "ecommerce:marketplace_report",
        "icon": "fas fa-chart-line",
        "order": 90,
    },
)


class Command(BaseCommand):
    help = "Create or update WPG Marketplace Core features and Admin access."

    @transaction.atomic
    def handle(self, *args, **options):
        anchor = (
            Feature.objects
            .select_related("business_unit")
            .filter(code="MARKETPLACE_DASHBOARD")
            .first()
        )
        if anchor is None or anchor.business_unit_id is None:
            raise CommandError(
                "MARKETPLACE_DASHBOARD with a BusinessUnit is required. "
                "Run the main Core seed command first."
            )

        business_unit = anchor.business_unit
        admin_group, unused_created = Group.objects.get_or_create(
            name="Admin"
        )

        created_count = 0
        updated_count = 0

        for definition in FEATURES:
            code = definition["code"]
            defaults = {
                key: value
                for key, value in definition.items()
                if key != "code"
            }
            defaults.update(
                {
                    "business_unit": business_unit,
                    "engine": None,
                    "is_active": True,
                }
            )

            feature, created = Feature.objects.update_or_create(
                code=code,
                defaults=defaults,
            )

            RoleFeature.objects.update_or_create(
                role=admin_group,
                feature=feature,
                defaults={
                    "can_view": True,
                    "can_add": True,
                    "can_edit": True,
                    "can_delete": True,
                    "can_approve": True,
                },
            )

            if created:
                created_count += 1
                action = "CREATED"
            else:
                updated_count += 1
                action = "UPDATED"

            self.stdout.write(
                f"{action}  {feature.code}  {feature.name}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Marketplace features seeded successfully: "
                f"{created_count} created, {updated_count} updated. "
                "Admin permissions granted."
            )
        )
