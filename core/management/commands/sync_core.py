from django.core.management.base import BaseCommand
from core.services import CoreSetupService


class Command(BaseCommand):
    help = "Synchronize WPG BOS Core configuration"

    def handle(self, *args, **options):

        self.stdout.write("")
        self.stdout.write("========================================")
        self.stdout.write(" WPG BOS CORE SYNCHRONIZATION")
        self.stdout.write("========================================")

        result = CoreSetupService.sync_all()

        for key, value in result.items():
            self.stdout.write("")
            self.stdout.write(key.replace("_", " ").title())
            self.stdout.write(f"  Created: {value['created']}")
            self.stdout.write(f"  Updated: {value['updated']}")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Core synchronization completed successfully.")
        )