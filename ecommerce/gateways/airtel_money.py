import os
from decimal import Decimal

import requests
from django.core.exceptions import ImproperlyConfigured

from .base import BasePaymentGateway, GatewayResult
from .registry import PaymentGatewayRegistry


@PaymentGatewayRegistry.register
class AirtelMoneyGateway(BasePaymentGateway):
    provider_code = "AIRTEL_MONEY"

    SUCCESS_STATUSES = {
        "TS",
        "SUCCESS",
        "SUCCESSFUL",
    }

    PENDING_STATUSES = {
        "TIP",
        "PENDING",
        "PROCESSING",
        "INITIATED",
    }

    FAILED_STATUSES = {
        "TF",
        "FAILED",
        "FAILURE",
        "REJECTED",
        "CANCELLED",
    }

    def __init__(self):
        self.base_url = self._required_setting(
            "AIRTEL_MONEY_BASE_URL"
        ).rstrip("/")

        self.client_id = self._required_setting(
            "AIRTEL_MONEY_CLIENT_ID"
        )
        self.client_secret = self._required_setting(
            "AIRTEL_MONEY_CLIENT_SECRET"
        )

        self.country = os.environ.get(
            "AIRTEL_MONEY_COUNTRY",
            "RW",
        ).strip().upper()

        self.currency = os.environ.get(
            "AIRTEL_MONEY_CURRENCY",
            "RWF",
        ).strip().upper()

        self.timeout = int(
            os.environ.get(
                "AIRTEL_MONEY_TIMEOUT",
                "30",
            )
        )

    @staticmethod
    def _required_setting(name):
        value = os.environ.get(name, "").strip()

        if not value:
            raise ImproperlyConfigured(
                f"{name} is required for Airtel Money."
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

        if (
            not value.startswith("250")
            or len(value) != 12
        ):
            raise ValueError(
                "Use a valid Rwanda Airtel Money number."
            )

        return value

    @staticmethod
    def _safe_json(response):
        try:
            payload = response.json()

            if isinstance(payload, dict):
                return payload

        except ValueError:
            pass

        return {}

    @classmethod
    def _normalise_status(cls, provider_status):
        status = str(
            provider_status or "UNKNOWN"
        ).strip().upper()

        if status in cls.SUCCESS_STATUSES:
            return "SUCCESSFUL"

        if status in cls.PENDING_STATUSES:
            return "PENDING"

        if status in cls.FAILED_STATUSES:
            return "FAILED"

        return "UNKNOWN"

    def _token(self):
        response = requests.post(
            f"{self.base_url}/auth/oauth2/token",
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        payload = self._safe_json(response)
        token = payload.get("access_token")

        if not token:
            raise RuntimeError(
                "Airtel Money did not return an access token."
            )

        return token

    def _headers(self, token):
        return {
            "Authorization": f"Bearer {token}",
            "X-Country": self.country,
            "X-Currency": self.currency,
            "Content-Type": "application/json",
            "Accept": "application/json",
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
        token = self._token()
        transaction_id = str(merchant_reference)

        payload = {
            "reference": merchant_reference,
            "subscriber": {
                "country": self.country,
                "currency": self.currency,
                "msisdn": self._rwanda_msisdn(
                    customer_reference
                ),
            },
            "transaction": {
                "amount": float(amount),
                "country": self.country,
                "currency": self.currency,
                "id": transaction_id,
            },
        }

        response = requests.post(
            f"{self.base_url}/merchant/v1/payments/",
            headers=self._headers(token),
            json=payload,
            timeout=self.timeout,
        )

        response_payload = self._safe_json(response)

        if response.status_code not in {200, 201, 202}:
            return GatewayResult(
                successful=False,
                provider_status="FAILED",
                provider_request_id=transaction_id,
                message=(
                    "Airtel Money rejected the payment request "
                    f"with HTTP {response.status_code}."
                ),
                raw_response=response_payload,
            )

        transaction = (
            response_payload.get("data", {})
            .get("transaction", {})
        )

        status = self._normalise_status(
            transaction.get("status", "PENDING")
        )

        return GatewayResult(
            successful=status != "FAILED",
            provider_status=status,
            provider_request_id=transaction_id,
            provider_reference=str(
                transaction.get("airtel_money_id", "")
                or transaction.get("id", "")
            ),
            message=(
                "Payment request sent to the customer's "
                "Airtel Money wallet."
            ),
            raw_response=response_payload,
        )

    def get_payment_status(
        self,
        *,
        provider_request_id: str,
    ):
        token = self._token()

        response = requests.get(
            (
                f"{self.base_url}/standard/v1/payments/"
                f"{provider_request_id}"
            ),
            headers=self._headers(token),
            timeout=self.timeout,
        )

        payload = self._safe_json(response)

        if response.status_code != 200:
            return GatewayResult(
                successful=False,
                provider_status="UNKNOWN",
                provider_request_id=provider_request_id,
                message=(
                    "Airtel Money status check returned "
                    f"HTTP {response.status_code}."
                ),
                raw_response=payload,
            )

        transaction = (
            payload.get("data", {})
            .get("transaction", {})
        )

        provider_status = self._normalise_status(
            transaction.get("status")
        )

        return GatewayResult(
            successful=True,
            provider_status=provider_status,
            provider_request_id=provider_request_id,
            provider_reference=str(
                transaction.get("airtel_money_id", "")
                or transaction.get("id", "")
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
            "Airtel Money provider refund will be enabled "
            "after WPG's Rwanda production refund contract "
            "has been approved."
        )