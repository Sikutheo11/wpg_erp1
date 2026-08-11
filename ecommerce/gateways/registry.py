from django.core.exceptions import ImproperlyConfigured

from .base import BasePaymentGateway


class PaymentGatewayRegistry:
    _gateways = {}

    @classmethod
    def register(cls, gateway_class):
        if not issubclass(gateway_class, BasePaymentGateway):
            raise TypeError(
                "Payment gateway must inherit BasePaymentGateway."
            )

        code = str(gateway_class.provider_code or "").strip().upper()
        if not code:
            raise ImproperlyConfigured(
                "Payment gateway must define provider_code."
            )

        cls._gateways[code] = gateway_class
        return gateway_class

    @classmethod
    def get(cls, provider_code):
        code = str(provider_code or "").strip().upper()

        try:
            gateway_class = cls._gateways[code]
        except KeyError as error:
            raise ImproperlyConfigured(
                f"Payment gateway {code or '<empty>'} is not registered."
            ) from error

        return gateway_class()

    @classmethod
    def registered_codes(cls):
        return tuple(sorted(cls._gateways))