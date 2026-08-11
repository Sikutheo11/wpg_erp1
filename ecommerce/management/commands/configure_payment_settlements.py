import os

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ecommerce.models import PaymentProviderConfiguration
from finance.models import Account
from finance.services.account_service import AccountService


class Command(BaseCommand):
    help = (
        "Configure WPG Ecommerce settlement accounts and "
        "payment-provider mappings."
    )

    ENVIRONMENT = {
        "MTN_MOMO": "WPG_MTN_MERCHANT_NUMBER",
        "AIRTEL_MONEY": "WPG_AIRTEL_MERCHANT_NUMBER",
        "BANK": "WPG_BANK_SETTLEMENT_ACCOUNT",
    }

    def _environment_value(self, name):
        value = os.environ.get(name, "").strip()

        if not value:
            raise CommandError(
                f"Required environment variable {name} is missing."
            )

        return value

    def _get_or_create_account(
        self,
        *,
        name,
        account_type,
        account_number,
    ):
        existing = Account.objects.filter(
            account_number=account_number,
        ).first()

        if existing is not None:
            if existing.account_type != account_type:
                raise CommandError(
                    f"Finance account {existing.name} has an "
                    "incompatible account type."
                )
            return existing, False

        try:
            account = AccountService.create_account(
                name=name,
                account_type=account_type,
                account_number=account_number,
                opening_balance=0,
            )
        except ValidationError as error:
            raise CommandError(
                "; ".join(error.messages)
            ) from error

        return account, True

    def _configure_provider(
        self,
        *,
        provider,
        account,
        sort_order,
    ):
        configuration, created = (
            PaymentProviderConfiguration.objects.update_or_create(
                provider=provider,
                defaults={
                    "settlement_account": account,
                    "is_active": True,
                    "sort_order": sort_order,
                },
            )
        )

        try:
            configuration.full_clean()
        except ValidationError as error:
            raise CommandError(
                "; ".join(error.messages)
            ) from error

        configuration.save()

        return configuration, created

    @transaction.atomic
    def handle(self, *args, **options):
        mtn_number = os.environ.get(
            self.ENVIRONMENT["MTN_MOMO"],
            "",
        ).strip()

        airtel_number = os.environ.get(
            self.ENVIRONMENT["AIRTEL_MONEY"],
            "",
        ).strip()

        bank_number = os.environ.get(
            self.ENVIRONMENT["BANK"],
            "",
        ).strip()

        if not any(
            [
                mtn_number,
                airtel_number,
                bank_number,
            ]
        ):
            raise CommandError(
                "No WPG payment settlement environment "
                "configuration was found."
            )

        configured = []

        if mtn_number:
            mtn_account, unused_created = (
                self._get_or_create_account(
                    name="WPG MTN MoMo Merchant",
                    account_type="mobile",
                    account_number=mtn_number,
                )
            )

            self._configure_provider(
                provider=PaymentProviderConfiguration.MTN_MOMO,
                account=mtn_account,
                sort_order=10,
            )

            configured.append(
                (
                    PaymentProviderConfiguration.MTN_MOMO,
                    mtn_account,
                )
            )

        if airtel_number:
            airtel_account, unused_created = (
                self._get_or_create_account(
                    name="WPG Airtel Money Merchant",
                    account_type="mobile",
                    account_number=airtel_number,
                )
            )

            self._configure_provider(
                provider=PaymentProviderConfiguration.AIRTEL_MONEY,
                account=airtel_account,
                sort_order=20,
            )

            configured.append(
                (
                    PaymentProviderConfiguration.AIRTEL_MONEY,
                    airtel_account,
                )
            )

        if bank_number:
            bank_account, unused_created = (
                self._get_or_create_account(
                    name="WPG Ecommerce Bank Settlement",
                    account_type="bank",
                    account_number=bank_number,
                )
            )

            for provider, sort_order in (
                (
                    PaymentProviderConfiguration.RSWITCH_CARD,
                    30,
                ),
                (
                    PaymentProviderConfiguration.EKASH,
                    40,
                ),
            ):
                self._configure_provider(
                    provider=provider,
                    account=bank_account,
                    sort_order=sort_order,
                )

                configured.append(
                    (
                        provider,
                        bank_account,
                    )
                )

        for provider, account in configured:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Configured {provider} → {account.name}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "WPG Ecommerce payment settlement configuration complete."
            )
        )