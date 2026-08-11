import os
import uuid
from decimal import Decimal

import requests
from django.core.exceptions import ImproperlyConfigured

from .base import BasePaymentGateway, GatewayResult
from .registry import PaymentGatewayRegistry


@PaymentGatewayRegistry.register
class MTNMoMoGateway(BasePaymentGateway):
    provider_code = "MTN_MOMO"

    def __init__(self):
        self.base_url = self._required_setting(
            "MTN_MOMO_BASE_URL"
        ).rstrip("/")
        self.subscription_key = self._required_setting(
            "MTN_MOMO_SUBSCRIPTION_KEY"
        )
        self.api_user = self._required_setting(
            "MTN_MOMO_API_USER"
        )
        self.api_key = self._required_setting(
            "MTN_MOMO_API_KEY"
        )
        self.target_environment = self._required_setting(
            "MTN_MOMO_TARGET_ENVIRONMENT"
        )
        self.timeout = int(
            os.environ.get("MTN_MOMO_TIMEOUT", "30")
        )

    @staticmethod
    def _required_setting(name):
        value = os.environ.get(name, "").strip()
        if not value:
            raise ImproperlyConfigured(
                f"{name} is required for MTN MoMo."
            )
        return value

    @staticmethod
    def _rwanda_msisdn(phone):
        value = "".join(
            character
            for character in str(phone or "")
            if character.isdigit()
        )

        if value.startswith("0"):
            value = f"250{value[1:]}"

        if not value.startswith("250"):
            raise ValueError(
                "Use a valid Rwanda Mobile Money number."
            )

        return value

    def _token(self):
        response = requests.post(
            f"{self.base_url}/collection/token/",
            headers={
                "Ocp-Apim-Subscription-Key": (
                    self.subscription_key
                ),
            },
            auth=(
                self.api_user,
                self.api_key,
            ),
            timeout=self.timeout,
        )

        response.raise_for_status()

        payload = response.json()
        token = payload.get("access_token")

        if not token:
            raise RuntimeError(
                "MTN MoMo did not return an access token."
            )

        return token

    def _headers(self, token):
        return {
            "Authorization": f"Bearer {token}",
            "Ocp-Apim-Subscription-Key": (
                self.subscription_key
            ),
            "X-Target-Environment": (
                self.target_environment
            ),
            "Content-Type": "application/json",
        }

    def initiate_payment(
        self,
        *,
        amount: Decimal,
        currency: str,
        customer_reference: str,
        merchant_reference: str,
        callback_url: str = "",
    ):
        request_id = str(uuid.uuid4())
        token = self._token()

        headers = self._headers(token)
        headers["X-Reference-Id"] = request_id

        if callback_url:
            headers["X-Callback-Url"] = callback_url


        provider_currency = (
            "EUR"
            if self.target_environment.lower() == "sandbox"
            else str(currency).upper()
        )

        payload = {
            "amount": str(amount),
            "currency": provider_currency,
            "externalId": merchant_reference,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": self._rwanda_msisdn(
                    customer_reference
                ),
            },
            "payerMessage": (
                f"WPG payment {merchant_reference}"
            )[:160],
            "payeeNote": (
                f"WPG Ecommerce {merchant_reference}"
            )[:160],
        }

        response = requests.post(
            (
                f"{self.base_url}"
                "/collection/v1_0/requesttopay"
            ),
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )

        if response.status_code != 202:
            return GatewayResult(
                successful=False,
                provider_status="FAILED",
                provider_request_id=request_id,
                message=(
                    f"MTN MoMo rejected the request "
                    f"with HTTP {response.status_code}."
                ),
                raw_response=self._safe_json(response),
            )

        return GatewayResult(
            successful=True,
            provider_status="PENDING",
            provider_request_id=request_id,
            message=(
                "Payment request sent to the customer's "
                "MTN MoMo wallet."
            ),
        )

    def get_payment_status(
        self,
        *,
        provider_request_id: str,
    ):
        token = self._token()

        response = requests.get(
            (
                f"{self.base_url}"
                "/collection/v1_0/requesttopay/"
                f"{provider_request_id}"
            ),
            headers=self._headers(token),
            timeout=self.timeout,
        )

        if response.status_code != 200:
            return GatewayResult(
                successful=False,
                provider_status="UNKNOWN",
                provider_request_id=provider_request_id,
                message=(
                    f"MTN status check returned "
                    f"HTTP {response.status_code}."
                ),
                raw_response=self._safe_json(response),
            )

        payload = response.json()
        status = str(
            payload.get("status", "UNKNOWN")
        ).upper()

        return GatewayResult(
            successful=True,
            provider_status=status,
            provider_request_id=provider_request_id,
            provider_reference=str(
                payload.get("financialTransactionId", "")
            ),
            raw_response=payload,
        )

    def refund_payment(
        self,
        *,
        provider_reference: str,
        amount: Decimal,
        currency: str,
        merchant_reference: str,
    ):
        raise ImproperlyConfigured(
            "MTN provider refund must be enabled only "
            "after WPG's production Collection/refund "
            "contract is confirmed."
        )

    @staticmethod
    def _safe_json(response):
        try:
            payload = response.json()
            return (
                payload
                if isinstance(payload, dict)
                else {}
            )
        except ValueError:
            return {}