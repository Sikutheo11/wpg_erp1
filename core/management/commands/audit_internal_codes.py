from django.core.management.base import BaseCommand

from core.internal_codes import audit_internal_code_policy


class Command(BaseCommand):
    help = "Audit every model field governed by the WPG automatic internal-code policy."

    def handle(self, *args, **options):
        rows = audit_internal_code_policy()
        self.stdout.write("WPG automatic internal-code audit")
        self.stdout.write("=" * 72)

        for row in rows:
            self.stdout.write(
                f"{row['model']}.{row['field']} | "
                f"prefix={row['prefix']} | "
                f"unique={row['unique']} | "
                f"blank={row['blank']} | "
                f"max_length={row['max_length']}"
            )

        self.stdout.write("=" * 72)
        self.stdout.write(self.style.SUCCESS(f"Detected {len(rows)} internal code field(s)."))
