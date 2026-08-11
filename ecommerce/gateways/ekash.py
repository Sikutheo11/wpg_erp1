from django.core.exceptions import ImproperlyConfigured

from .base import BasePaymentGateway
from .registry import PaymentGatewayRegistry


@PaymentGatewayRegistry.register
class EKashGateway(BasePaymentGateway):
    provider_code = "EKASH"

    @staticmethod
    def _api_contract_required():
        raise ImproperlyConfigured(
            "eKash gateway is registered but its RSwitch Merchant API "
            "contract has not yet been configured."
        )

    def initiate_payment(self, **kwargs):
        self._api_contract_required()

    def get_payment_status(self, **kwargs):
        self._api_contract_required()

    def refund_payment(self, **kwargs):
        self._api_contract_required()