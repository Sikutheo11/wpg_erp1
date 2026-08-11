from datetime import timedelta

from django.core.exceptions import (
    ImproperlyConfigured,
    ValidationError,
)
from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db.models import Q
from django.utils import timezone
from requests import RequestException

from ecommerce.models import EcommercePayment
from ecommerce.services import EcommercePaymentService


class Command(BaseCommand):
    help = (
        "Check pending automated Ecommerce payments "
        "against their payment providers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help=(
                "Maximum number of pending payments "
                "to check. Default: 50."
            ),
        )
        parser.add_argument(
            "--min-age",
            type=int,
            default=2,
            help=(
                "Minutes since initiation or the last "
                "status check. Default: 2."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "List eligible payments without contacting "
                "payment providers."
            ),
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        min_age = options["min_age"]
        dry_run = options["dry_run"]

        if limit < 1:
            raise CommandError(
                "--limit must be greater than zero."
            )

        if min_age < 0:
            raise CommandError(
                "--min-age cannot be negative."
            )

        cutoff = timezone.now() - timedelta(
            minutes=min_age
        )

        queryset = (
            EcommercePayment.objects
            .select_related(
                "checkout",
            )
            .filter(
                status=EcommercePayment.PENDING,
                provider__in=(
                    EcommercePaymentService
                    .AUTOMATED_PROVIDERS
                ),
                initiated_at__lte=cutoff,
            )
            .exclude(
                provider_request_id="",
            )
            .filter(
                Q(last_status_check_at__isnull=True)
                | Q(last_status_check_at__lte=cutoff)
            )
            .order_by(
                "last_status_check_at",
                "initiated_at",
                "pk",
            )
        )

        payments = list(queryset[:limit])

        if not payments:
            self.stdout.write(
                self.style.SUCCESS(
                    "No pending Ecommerce payments "
                    "require reconciliation."
                )
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    (
                        f"DRY RUN: {len(payments)} payment(s) "
                        "would be checked."
                    )
                )
            )

            for payment in payments:
                self.stdout.write(
                    (
                        f"{payment.payment_number} | "
                        f"{payment.provider} | "
                        f"{payment.status} | "
                        f"{payment.amount} "
                        f"{payment.currency}"
                    )
                )

            return

        confirmed = 0
        failed = 0
        pending = 0
        errors = 0

        for payment in payments:
            try:
                payment, unused_changed = (
                    EcommercePaymentService
                    .check_provider_status(
                        payment=payment,
                        actor=None,
                    )
                )
            except (
                ValidationError,
                ImproperlyConfigured,
                RequestException,
                RuntimeError,
                ValueError,
            ) as error:
                errors += 1

                self.stderr.write(
                    self.style.ERROR(
                        (
                            f"ERROR {payment.payment_number}: "
                            f"{error}"
                        )
                    )
                )
                continue

            payment.refresh_from_db()

            if (
                payment.status
                == EcommercePayment.CONFIRMED
            ):
                confirmed += 1
                result_style = self.style.SUCCESS

            elif payment.status == EcommercePayment.FAILED:
                failed += 1
                result_style = self.style.ERROR

            else:
                pending += 1
                result_style = self.style.WARNING

            self.stdout.write(
                result_style(
                    (
                        f"{payment.payment_number} → "
                        f"{payment.status} "
                        f"({payment.provider_status or 'UNKNOWN'})"
                    )
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Reconciliation complete: "
                    f"checked={len(payments)}, "
                    f"confirmed={confirmed}, "
                    f"failed={failed}, "
                    f"pending={pending}, "
                    f"errors={errors}."
                )
            )
        )