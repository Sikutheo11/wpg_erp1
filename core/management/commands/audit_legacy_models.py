from django.core.management.base import BaseCommand, CommandError

from furniture.models import Order as LegacyFurnitureOrder, ProductionOutput
from sales.models import CustomerPayment, Invoice, Sale, SaleItem


class Command(BaseCommand):
    help = "Report records that must be migrated before legacy models are removed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--require-empty",
            action="store_true",
            help="Fail when any legacy records or references remain.",
        )

    def handle(self, *args, **options):
        counts = {
            "furniture.Order": LegacyFurnitureOrder.objects.count(),
            "sales.Sale": Sale.objects.count(),
            "sales.SaleItem": SaleItem.objects.count(),
            "sales.Invoice": Invoice.objects.count(),
            "sales.CustomerPayment": CustomerPayment.objects.count(),
            "furniture.ProductionOutput.legacy_order": ProductionOutput.objects.filter(
                legacy_order__isnull=False
            ).count(),
        }

        self.stdout.write("=== LEGACY MODEL RETIREMENT AUDIT ===")
        for label, count in counts.items():
            self.stdout.write(f"{label}: {count}")

        remaining = sum(counts.values())
        self.stdout.write(f"LEGACY_RETIREMENT_SUMMARY: remaining={remaining}")

        if options["require_empty"] and remaining:
            raise CommandError(
                "Legacy records remain. Export and migrate them before model removal."
            )

