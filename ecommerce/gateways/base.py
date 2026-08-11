from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class GatewayResult:
    successful: bool
    provider_status: str
    provider_request_id: str = ""
    provider_reference: str = ""
    message: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)


class BasePaymentGateway(ABC):
    provider_code = ""

    @abstractmethod
    def initiate_payment(
        self,
        *,
        amount: Decimal,
        currency: str,
        customer_reference: str,
        merchant_reference: str,
        callback_url: str = "",
    ) -> GatewayResult:
        raise NotImplementedError

    @abstractmethod
    def get_payment_status(
        self,
        *,
        provider_request_id: str,
    ) -> GatewayResult:
        raise NotImplementedError

    @abstractmethod
    def refund_payment(
        self,
        *,
        provider_reference: str,
        amount: Decimal,
        currency: str,
        merchant_reference: str,
    ) -> GatewayResult:
        raise NotImplementedError