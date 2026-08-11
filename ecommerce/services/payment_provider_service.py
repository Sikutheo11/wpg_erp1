from django.core.exceptions import ValidationError
from ..gateways import PaymentGatewayRegistry
from ..models import PaymentProviderConfiguration


class PaymentProviderConfigurationService:
    """
    Resolves Ecommerce payment providers to WPG settlement accounts.

    Provider API credentials are intentionally kept outside the database.
    """

    FINANCE_METHODS = {
        PaymentProviderConfiguration.MTN_MOMO: "mobile_money",
        PaymentProviderConfiguration.AIRTEL_MONEY: "mobile_money",
        PaymentProviderConfiguration.RSWITCH_CARD: "bank",
        PaymentProviderConfiguration.EKASH: "bank",
    }

    CUSTOMER_READY_PROVIDERS = {
        PaymentProviderConfiguration.MTN_MOMO,
        PaymentProviderConfiguration.AIRTEL_MONEY,
    }

    @classmethod
    def customer_provider_choices(cls):
        """
        Return providers that are implemented, registered and enabled
        for WPG customer payments.
        """
        registered_providers = set(
            PaymentGatewayRegistry.registered_codes()
        )

        enabled_providers = set(
            PaymentProviderConfiguration.objects.filter(
                is_active=True,
                provider__in=cls.CUSTOMER_READY_PROVIDERS,
            ).values_list(
                "provider",
                flat=True,
            )
        )

        available_providers = (
            registered_providers
            & enabled_providers
            & cls.CUSTOMER_READY_PROVIDERS
        )

        labels = dict(
            PaymentProviderConfiguration.PROVIDERS
        )

        configurations = (
            PaymentProviderConfiguration.objects
            .filter(
                provider__in=available_providers,
                is_active=True,
            )
            .order_by(
                "sort_order",
                "provider",
            )
        )

        return tuple(
            (
                configuration.provider,
                labels[configuration.provider],
            )
            for configuration in configurations
        )

    @classmethod
    def customer_provider_is_available(
        cls,
        provider,
    ):
        try:
            provider = cls.normalize_provider(provider)
        except ValidationError:
            return False

        if provider not in cls.CUSTOMER_READY_PROVIDERS:
            return False

        if (
            provider
            not in PaymentGatewayRegistry.registered_codes()
        ):
            return False

        return PaymentProviderConfiguration.objects.filter(
            provider=provider,
            is_active=True,
        ).exists()

    @classmethod
    def require_customer_provider(cls, provider):
        provider = cls.normalize_provider(provider)

        if not cls.customer_provider_is_available(provider):
            raise ValidationError(
                {
                    "provider": (
                        f"{provider} is not currently available "
                        "for customer payments."
                    )
                }
            )

        return provider

    @classmethod
    def normalize_provider(cls, provider):
        provider = str(provider or "").strip().upper()

        valid_providers = {
            code
            for code, unused_label
            in PaymentProviderConfiguration.PROVIDERS
        }

        if provider not in valid_providers:
            raise ValidationError(
                {
                    "provider": (
                        f"Unsupported payment provider: "
                        f"{provider or '<empty>'}."
                    )
                }
            )

        return provider

    @classmethod
    def finance_payment_method(cls, provider):
        provider = cls.normalize_provider(provider)

        return cls.FINANCE_METHODS[provider]

    @classmethod
    def get_configuration(cls, provider):
        provider = cls.normalize_provider(provider)

        try:
            return (
                PaymentProviderConfiguration.objects
                .select_related("settlement_account")
                .get(
                    provider=provider,
                    is_active=True,
                )
            )
        except PaymentProviderConfiguration.DoesNotExist as error:
            raise ValidationError(
                {
                    "provider": (
                        f"{provider} is not configured for "
                        "WPG Ecommerce payments."
                    )
                }
            ) from error

    @classmethod
    def get_settlement_account(cls, provider):
        configuration = cls.get_configuration(provider)

        account = configuration.settlement_account

        expected_type = (
            "mobile"
            if cls.finance_payment_method(provider)
            == "mobile_money"
            else "bank"
        )

        if account.account_type != expected_type:
            raise ValidationError(
                {
                    "settlement_account": (
                        f"{provider} requires a Finance "
                        f"{expected_type} account."
                    )
                }
            )

        return account