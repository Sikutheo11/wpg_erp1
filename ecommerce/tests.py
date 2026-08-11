from decimal import Decimal
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
import os
from io import StringIO
from django.core.management import call_command
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from django.core import signing
from django.urls import reverse
from ecommerce.gateways.mtn_momo import MTNMoMoGateway
from agriculture.models import PoultryFarm
from finance.models import JournalEntry, LedgerAccount
from inventory.models import Product
from orders.models import Order, OrderItem
from ecommerce.forms import EcommercePaymentForm
from ecommerce.models import (
    EcommerceCheckout,
    EcommerceCheckoutOrder,
    EcommercePayment,
    MarketplaceOrderLine,
    MarketplaceSeller,
    OnlineProduct,
    SellerProductAssignment,
    SellerSettlement,
    PaymentProviderConfiguration,
)

from ecommerce.services import (
    EcommercePaymentService,
    MarketplaceCommissionService,
    SellerSettlementService,
)

from ecommerce.gateways import GatewayResult
from ecommerce.gateways.airtel_money import (
    AirtelMoneyGateway,
)
from finance.models import (
    Account,
    JournalEntry,
    LedgerAccount,
)

class EcommercePaymentFormSecurityTests(TestCase):
    def setUp(self):
        self.mobile_account = Account.objects.create(
            name="WPG Test Mobile Money",
            account_type="mobile",
            account_number="TEST-MOBILE-001",
        )

        self.mtn_configuration = (
            PaymentProviderConfiguration.objects.create(
                provider="MTN_MOMO",
                settlement_account=self.mobile_account,
                is_active=True,
                sort_order=10,
            )
        )

    def test_only_active_configured_provider_is_shown(
        self,
    ):
        form = EcommercePaymentForm()

        self.assertEqual(
            tuple(form.fields["provider"].choices),
            (("MTN_MOMO", "MTN MoMo"),),
        )
        self.assertTrue(
            form.has_available_providers
        )

    def test_post_cannot_select_unconfigured_airtel(
        self,
    ):
        form = EcommercePaymentForm(
            data={
                "provider": "AIRTEL_MONEY",
                "method": EcommercePayment.MOBILE_MONEY,
                "customer_reference": "0738000000",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "provider",
            form.errors,
        )

    def test_provider_overrides_forged_payment_method(
        self,
    ):
        form = EcommercePaymentForm(
            data={
                "provider": "MTN_MOMO",
                "method": EcommercePayment.BANK,
                "customer_reference": "0788000000",
            }
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
        self.assertEqual(
            form.cleaned_data["method"],
            EcommercePayment.MOBILE_MONEY,
        )

    def test_no_configuration_disables_payment(
        self,
    ):
        self.mtn_configuration.is_active = False
        self.mtn_configuration.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        form = EcommercePaymentForm(
            data={
                "provider": "MTN_MOMO",
                "customer_reference": "0788000000",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertFalse(
            form.has_available_providers
        )


class MarketplaceCommissionCalculationTests(SimpleTestCase):
    def test_five_percent_commission_is_calculated_correctly(self):
        result = MarketplaceCommissionService.calculate_amounts(
            quantity=Decimal("2.00"),
            unit_price=Decimal("200.00"),
            commission_rate=Decimal("5.00"),
        )

        self.assertEqual(result["gross_amount"], Decimal("400.00"))
        self.assertEqual(result["commission_amount"], Decimal("20.00"))
        self.assertEqual(result["seller_net_amount"], Decimal("380.00"))

    def test_commission_rounds_to_two_decimal_places(self):
        result = MarketplaceCommissionService.calculate_amounts(
            quantity=Decimal("3.00"),
            unit_price=Decimal("333.33"),
            commission_rate=Decimal("7.50"),
        )

        self.assertEqual(result["gross_amount"], Decimal("999.99"))
        self.assertEqual(result["commission_amount"], Decimal("75.00"))
        self.assertEqual(result["seller_net_amount"], Decimal("924.99"))

    def test_invalid_commission_rate_is_rejected(self):
        for invalid_rate in (Decimal("-1.00"), Decimal("101.00")):
            with self.subTest(rate=invalid_rate):
                with self.assertRaises(ValidationError):
                    MarketplaceCommissionService.calculate_amounts(
                        quantity=1,
                        unit_price=200,
                        commission_rate=invalid_rate,
                    )

    def test_non_positive_quantity_is_rejected(self):
        with self.assertRaises(ValidationError):
            MarketplaceCommissionService.calculate_amounts(
                quantity=0,
                unit_price=200,
                commission_rate=5,
            )


class MarketplaceSettlementLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mobile_money_account = LedgerAccount.objects.create(
            code="1120",
            name="Mobile Money",
            account_type=LedgerAccount.ASSET,
            normal_balance=LedgerAccount.DEBIT,
            business_unit="",
            is_control_account=False,
            is_active=True,
        )
        cls.seller_payable_account = LedgerAccount.objects.create(
            code="2200",
            name="Marketplace Seller Payables",
            account_type=LedgerAccount.LIABILITY,
            normal_balance=LedgerAccount.CREDIT,
            business_unit="MARKETPLACE",
            is_control_account=True,
            is_active=True,
        )

        cls.farm = PoultryFarm.objects.create(
            code="TEST-FARM",
            name="Test Poultry Farm",
            location="Karongi",
            is_active=True,
        )
        cls.product = Product.objects.create(
            name="Test Eggs",
            business_unit="AGRICULTURE",
            product_type="AGRICULTURE_OUTPUT",
            selling_price=Decimal("200.00"),
            standard_cost=Decimal("120.00"),
            unit="pcs",
            is_active=True,
            is_published=True,
        )
        cls.online_product = OnlineProduct.objects.create(
            product=cls.product,
            title="Test Farm Eggs",
            purchase_mode=OnlineProduct.ADD_TO_CART,
            minimum_order_quantity=1,
        )
        cls.seller = MarketplaceSeller.objects.create(
            name="Test Independent Seller",
            seller_type=MarketplaceSeller.INDEPENDENT,
            poultry_farm=cls.farm,
            default_commission_rate=Decimal("5.00"),
            payable_account=cls.seller_payable_account,
            is_active=True,
        )
        SellerProductAssignment.objects.create(
            online_product=cls.online_product,
            seller=cls.seller,
            commission_rate=Decimal("5.00"),
            effective_from=timezone.localdate(),
            is_active=True,
        )

    def setUp(self):
        event_patcher = patch(
            "ecommerce.services.seller_settlement_service."
            "EventEngine.dispatch"
        )
        self.mock_dispatch = event_patcher.start()
        self.addCleanup(event_patcher.stop)

        self.order = Order.objects.create(
            business_unit="AGRICULTURE",
            order_type="ECOMMERCE",
            status="DELIVERED",
            payment_status="PAID",
            delivery_status="DELIVERED",
            customer_name="Test Customer",
            customer_phone="0788000000",
            subtotal=Decimal("400.00"),
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.online_product.display_title,
            quantity=2,
            price=Decimal("200.00"),
        )
        self.marketplace_line, created = (
            MarketplaceCommissionService.create_order_line(
                order_item=self.order_item,
                online_product=self.online_product,
            )
        )
        self.assertTrue(created)
        self.marketplace_line.settlement_status = (
            MarketplaceOrderLine.ELIGIBLE
        )
        self.marketplace_line.eligible_at = timezone.now()
        self.marketplace_line.save(
            update_fields=[
                "settlement_status",
                "eligible_at",
                "updated_at",
            ]
        )

    def _create_settlement(self):
        return SellerSettlementService.create_settlement(
            seller=self.seller,
            notes="Automated Marketplace test.",
        )

    def _approve_settlement(self, settlement):
        approved, changed = SellerSettlementService.approve_settlement(
            settlement=settlement,
        )
        self.assertTrue(changed)
        return approved

    def _pay_settlement(self, settlement):
        paid, created = SellerSettlementService.pay_settlement(
            settlement=settlement,
            payment_method="mobile_money",
            payment_reference="TEST-MOMO-001",
        )
        self.assertTrue(created)
        return paid

    def test_order_line_snapshot_is_correct_and_idempotent(self):
        line = self.marketplace_line

        self.assertEqual(line.seller, self.seller)
        self.assertEqual(line.farm, self.farm)
        self.assertEqual(line.seller_name, self.seller.name)
        self.assertEqual(line.product_name, "Test Farm Eggs")
        self.assertEqual(line.gross_amount, Decimal("400.00"))
        self.assertEqual(line.commission_rate, Decimal("5.00"))
        self.assertEqual(line.commission_amount, Decimal("20.00"))
        self.assertEqual(line.seller_net_amount, Decimal("380.00"))

        existing, created = MarketplaceCommissionService.create_order_line(
            order_item=self.order_item,
            online_product=self.online_product,
        )
        self.assertFalse(created)
        self.assertEqual(existing.pk, line.pk)
        self.assertEqual(
            MarketplaceOrderLine.objects.filter(
                order_item=self.order_item
            ).count(),
            1,
        )

    def test_create_settlement_moves_line_to_in_settlement(self):
        settlement = self._create_settlement()
        self.marketplace_line.refresh_from_db()

        self.assertEqual(settlement.status, SellerSettlement.DRAFT)
        self.assertEqual(settlement.total_gross, Decimal("400.00"))
        self.assertEqual(settlement.total_commission, Decimal("20.00"))
        self.assertEqual(settlement.total_payable, Decimal("380.00"))
        self.assertEqual(settlement.lines.count(), 1)
        self.assertEqual(
            self.marketplace_line.settlement_status,
            MarketplaceOrderLine.IN_SETTLEMENT,
        )

    def test_same_line_cannot_be_added_to_second_settlement(self):
        self._create_settlement()

        with self.assertRaises(ValidationError):
            self._create_settlement()

        self.assertEqual(SellerSettlement.objects.count(), 1)

    def test_approve_and_pay_posts_balanced_journal(self):
        settlement = self._create_settlement()
        settlement = self._approve_settlement(settlement)
        settlement = self._pay_settlement(settlement)

        settlement.refresh_from_db()
        self.marketplace_line.refresh_from_db()
        entry = settlement.journal_entry

        self.assertEqual(settlement.status, SellerSettlement.PAID)
        self.assertEqual(settlement.payment_reference, "TEST-MOMO-001")
        self.assertEqual(entry.status, JournalEntry.POSTED)
        self.assertEqual(
            entry.source_type,
            "MARKETPLACE_SELLER_SETTLEMENT",
        )
        self.assertTrue(entry.is_balanced)
        self.assertEqual(entry.total_debit, Decimal("380.00"))
        self.assertEqual(entry.total_credit, Decimal("380.00"))
        self.assertEqual(
            self.marketplace_line.settlement_status,
            MarketplaceOrderLine.SETTLED,
        )

        journal_lines = {
            line.account.code: line
            for line in entry.lines.select_related("account")
        }
        self.assertEqual(
            journal_lines["2200"].debit,
            Decimal("380.00"),
        )
        self.assertEqual(
            journal_lines["1120"].credit,
            Decimal("380.00"),
        )

    def test_payment_is_idempotent(self):
        settlement = self._create_settlement()
        settlement = self._approve_settlement(settlement)
        settlement = self._pay_settlement(settlement)
        journal_entry_id = settlement.journal_entry_id

        same_settlement, created = (
            SellerSettlementService.pay_settlement(
                settlement=settlement,
                payment_method="mobile_money",
                payment_reference="SHOULD-NOT-POST-AGAIN",
            )
        )

        self.assertFalse(created)
        self.assertEqual(
            same_settlement.journal_entry_id,
            journal_entry_id,
        )
        self.assertEqual(
            JournalEntry.objects.filter(
                source_type="MARKETPLACE_SELLER_SETTLEMENT",
                source_id=str(settlement.pk),
            ).count(),
            1,
        )

    def test_cancel_draft_releases_line_for_future_settlement(self):
        settlement = self._create_settlement()

        cancelled, changed = SellerSettlementService.cancel_settlement(
            settlement=settlement,
            reason="Incorrect settlement selection.",
        )
        self.marketplace_line.refresh_from_db()

        self.assertTrue(changed)
        self.assertEqual(cancelled.status, SellerSettlement.CANCELLED)
        self.assertEqual(cancelled.lines.count(), 0)
        self.assertEqual(
            self.marketplace_line.settlement_status,
            MarketplaceOrderLine.ELIGIBLE,
        )

        replacement = self._create_settlement()
        self.assertEqual(replacement.lines.count(), 1)

    def test_cancellation_requires_reason(self):
        settlement = self._create_settlement()

        with self.assertRaises(ValidationError):
            SellerSettlementService.cancel_settlement(
                settlement=settlement,
                reason="",
            )

    def test_paid_settlement_cannot_be_cancelled(self):
        settlement = self._create_settlement()
        settlement = self._approve_settlement(settlement)
        settlement = self._pay_settlement(settlement)

        with self.assertRaises(ValidationError):
            SellerSettlementService.cancel_settlement(
                settlement=settlement,
                reason="Attempted cancellation after payment.",
            )

    def test_internal_seller_cannot_have_settlement(self):
        internal_seller = MarketplaceSeller.objects.create(
            name="WPG Internal Test",
            seller_type=MarketplaceSeller.WPG_INTERNAL,
            default_commission_rate=Decimal("0.00"),
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            SellerSettlementService.create_settlement(
                seller=internal_seller,
            )

class MTNMoMoGatewayTests(SimpleTestCase):
    def setUp(self):
        self.environment = {
            "MTN_MOMO_BASE_URL": "https://sandbox.momo.test",
            "MTN_MOMO_SUBSCRIPTION_KEY": "test-subscription-key",
            "MTN_MOMO_API_USER": "test-api-user",
            "MTN_MOMO_API_KEY": "test-api-key",
            "MTN_MOMO_TARGET_ENVIRONMENT": "sandbox",
            "MTN_MOMO_TIMEOUT": "10",
        }

    @patch.dict(os.environ, {}, clear=False)
    @patch("ecommerce.gateways.mtn_momo.requests.post")
    def test_request_to_pay_becomes_pending(
        self,
        mock_post,
    ):
        os.environ.update(self.environment)

        token_response = MagicMock()
        token_response.json.return_value = {
            "access_token": "test-token",
        }
        token_response.raise_for_status.return_value = None

        request_response = MagicMock()
        request_response.status_code = 202

        mock_post.side_effect = [
            token_response,
            request_response,
        ]

        gateway = MTNMoMoGateway()

        result = gateway.initiate_payment(
            amount=Decimal("200.00"),
            currency="RWF",
            customer_reference="0788000000",
            merchant_reference="EPAY-TEST-001",
        )

        self.assertTrue(result.successful)
        self.assertEqual(
            result.provider_status,
            "PENDING",
        )
        self.assertTrue(result.provider_request_id)

        request_call = mock_post.call_args_list[1]

        payload = request_call.kwargs["json"]

        self.assertEqual(
            payload["amount"],
            "200.00",
        )
        self.assertEqual(
            payload["currency"],
            "EUR",
        )
        self.assertEqual(
            payload["externalId"],
            "EPAY-TEST-001",
        )
        self.assertEqual(
            payload["payer"]["partyId"],
            "250788000000",
        )

        headers = request_call.kwargs["headers"]

        self.assertIn(
            "X-Reference-Id",
            headers,
        )
        self.assertEqual(
            headers["X-Target-Environment"],
            "sandbox",
        )

    @patch.dict(os.environ, {}, clear=False)
    @patch("ecommerce.gateways.mtn_momo.requests.get")
    @patch("ecommerce.gateways.mtn_momo.requests.post")
    def test_successful_status_returns_transaction_reference(
        self,
        mock_post,
        mock_get,
    ):
        os.environ.update(self.environment)

        token_response = MagicMock()
        token_response.json.return_value = {
            "access_token": "test-token",
        }
        token_response.raise_for_status.return_value = None

        mock_post.return_value = token_response

        status_response = MagicMock()
        status_response.status_code = 200
        status_response.json.return_value = {
            "status": "SUCCESSFUL",
            "financialTransactionId": "MTN-TXN-123456",
            "amount": "200.00",
            "currency": "RWF",
        }

        mock_get.return_value = status_response

        gateway = MTNMoMoGateway()

        result = gateway.get_payment_status(
            provider_request_id=(
                "11111111-2222-4333-8444-555555555555"
            ),
        )

        self.assertTrue(result.successful)
        self.assertEqual(
            result.provider_status,
            "SUCCESSFUL",
        )
        self.assertEqual(
            result.provider_reference,
            "MTN-TXN-123456",
        )


class AirtelMoneyGatewayTests(SimpleTestCase):
    def setUp(self):
        self.environment = {
            "AIRTEL_MONEY_BASE_URL": (
                "https://openapiuat.airtel.test"
            ),
            "AIRTEL_MONEY_CLIENT_ID": (
                "test-airtel-client-id"
            ),
            "AIRTEL_MONEY_CLIENT_SECRET": (
                "test-airtel-client-secret"
            ),
            "AIRTEL_MONEY_COUNTRY": "RW",
            "AIRTEL_MONEY_CURRENCY": "RWF",
            "AIRTEL_MONEY_TIMEOUT": "10",
        }

    @patch.dict(os.environ, {}, clear=False)
    @patch(
        "ecommerce.gateways.airtel_money.requests.post"
    )
    def test_airtel_payment_request_becomes_pending(
        self,
        mock_post,
    ):
        os.environ.update(self.environment)

        token_response = MagicMock()
        token_response.json.return_value = {
            "access_token": "test-airtel-token",
        }
        token_response.raise_for_status.return_value = None

        payment_response = MagicMock()
        payment_response.status_code = 200
        payment_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": "EPAY-AIRTEL-001",
                    "status": "TIP",
                }
            },
            "status": {
                "success": True,
            },
        }

        mock_post.side_effect = [
            token_response,
            payment_response,
        ]

        gateway = AirtelMoneyGateway()

        result = gateway.initiate_payment(
            amount=Decimal("200.00"),
            currency="RWF",
            customer_reference="0738000000",
            merchant_reference="EPAY-AIRTEL-001",
        )

        self.assertTrue(result.successful)
        self.assertEqual(
            result.provider_status,
            "PENDING",
        )
        self.assertEqual(
            result.provider_request_id,
            "EPAY-AIRTEL-001",
        )

        token_call = mock_post.call_args_list[0]

        self.assertEqual(
            token_call.args[0],
            (
                "https://openapiuat.airtel.test"
                "/auth/oauth2/token"
            ),
        )
        self.assertEqual(
            token_call.kwargs["json"]["grant_type"],
            "client_credentials",
        )

        payment_call = mock_post.call_args_list[1]
        payload = payment_call.kwargs["json"]

        self.assertEqual(
            payload["subscriber"]["msisdn"],
            "250738000000",
        )
        self.assertEqual(
            payload["subscriber"]["country"],
            "RW",
        )
        self.assertEqual(
            payload["subscriber"]["currency"],
            "RWF",
        )
        self.assertEqual(
            payload["transaction"]["amount"],
            200.0,
        )
        self.assertEqual(
            payload["transaction"]["id"],
            "EPAY-AIRTEL-001",
        )

        headers = payment_call.kwargs["headers"]

        self.assertEqual(
            headers["X-Country"],
            "RW",
        )
        self.assertEqual(
            headers["X-Currency"],
            "RWF",
        )
        self.assertEqual(
            headers["Authorization"],
            "Bearer test-airtel-token",
        )

    @patch.dict(os.environ, {}, clear=False)
    @patch(
        "ecommerce.gateways.airtel_money.requests.get"
    )
    @patch(
        "ecommerce.gateways.airtel_money.requests.post"
    )
    def test_airtel_success_status_returns_reference(
        self,
        mock_post,
        mock_get,
    ):
        os.environ.update(self.environment)

        token_response = MagicMock()
        token_response.json.return_value = {
            "access_token": "test-airtel-token",
        }
        token_response.raise_for_status.return_value = None
        mock_post.return_value = token_response

        status_response = MagicMock()
        status_response.status_code = 200
        status_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": "EPAY-AIRTEL-001",
                    "airtel_money_id": (
                        "AIRTEL-RW-TXN-123456"
                    ),
                    "status": "TS",
                }
            },
            "status": {
                "success": True,
            },
        }

        mock_get.return_value = status_response

        gateway = AirtelMoneyGateway()

        result = gateway.get_payment_status(
            provider_request_id="EPAY-AIRTEL-001",
        )

        self.assertTrue(result.successful)
        self.assertEqual(
            result.provider_status,
            "SUCCESSFUL",
        )
        self.assertEqual(
            result.provider_reference,
            "AIRTEL-RW-TXN-123456",
        )

        self.assertEqual(
            mock_get.call_args.args[0],
            (
                "https://openapiuat.airtel.test"
                "/standard/v1/payments/"
                "EPAY-AIRTEL-001"
            ),
        )

class MTNMoMoPaymentIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mobile_money_account = LedgerAccount.objects.create(
            code="1120",
            name="Mobile Money",
            account_type=LedgerAccount.ASSET,
            normal_balance=LedgerAccount.DEBIT,
            business_unit="",
            is_control_account=False,
            is_active=True,
        )

        cls.customer_advances_account = LedgerAccount.objects.create(
            code="2100",
            name="Customer Advances",
            account_type=LedgerAccount.LIABILITY,
            normal_balance=LedgerAccount.CREDIT,
            business_unit="",
            is_control_account=True,
            is_active=True,
        )

    def setUp(self):
        self.checkout = EcommerceCheckout.objects.create(
            status="ORDERED",
            customer_name="MTN Test Customer",
            customer_phone="0788000000",
            currency="RWF",
            subtotal=Decimal("200.00"),
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
        )

        self.order = Order.objects.create(
            business_unit="AGRICULTURE",
            order_type="ECOMMERCE",
            status="PENDING",
            payment_status="UNPAID",
            customer_name="MTN Test Customer",
            customer_phone="0788000000",
            subtotal=Decimal("200.00"),
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
        )

        EcommerceCheckoutOrder.objects.create(
            checkout=self.checkout,
            order=self.order,
            business_unit="AGRICULTURE",
            amount=Decimal("200.00"),
        )

        self.payment = EcommercePayment.objects.create(
            checkout=self.checkout,
            method=EcommercePayment.MOBILE_MONEY,
            provider="MTN_MOMO",
            amount=Decimal("200.00"),
            currency="RWF",
            customer_reference="0788000000",
            status=EcommercePayment.PENDING,
            provider_request_id=(
                "11111111-2222-4333-8444-555555555555"
            ),
        )

    def test_mtn_payment_cannot_be_confirmed_manually(self):
        with self.assertRaisesMessage(
            ValidationError,
            "cannot be confirmed manually",
        ):
            EcommercePaymentService.confirm_payment(
                payment=self.payment,
                provider_reference="MANUAL-MTN-REFERENCE",
            )

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.checkout.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            EcommercePayment.PENDING,
        )
        self.assertIsNone(
            self.payment.customer_advance_id
        )

        self.assertEqual(
            self.order.status,
            "PENDING",
        )
        self.assertEqual(
            self.order.payment_status,
            "UNPAID",
        )

        self.assertEqual(
            self.checkout.status,
            "ORDERED",
        )

        self.assertFalse(
            JournalEntry.objects.filter(
                source_type="CUSTOMER_ADVANCE_RECEIPT",
            ).exists()
        )


    @patch(
        "finance.services.customer_advance_service.EventEngine.dispatch"
    )
    @patch(
        "ecommerce.services.payment_service.EventEngine.dispatch"
    )
    @patch(
        "ecommerce.services.payment_service.OrderService.confirm"
    )
    @patch(
        "ecommerce.services.payment_service.PaymentGatewayRegistry.get"
    )



    def test_mtn_success_confirms_payment_and_posts_customer_advance(
        self,
        mock_gateway_get,
        mock_order_confirm,
        unused_payment_dispatch,
        unused_finance_dispatch,
    ):
        gateway = MagicMock()

        gateway.get_payment_status.return_value = GatewayResult(
            successful=True,
            provider_status="SUCCESSFUL",
            provider_request_id=self.payment.provider_request_id,
            provider_reference="MTN-TXN-WPG-001",
            raw_response={
                "status": "SUCCESSFUL",
                "financialTransactionId": "MTN-TXN-WPG-001",
                "amount": "200.00",
                "currency": "RWF",
            },
        )

        mock_gateway_get.return_value = gateway

        def confirm_order(*, order, actor=None):
            order.status = "CONFIRMED"
            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )
            return order, {}

        mock_order_confirm.side_effect = confirm_order

        payment, changed = (
            EcommercePaymentService.check_provider_status(
                payment=self.payment,
            )
        )

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertTrue(changed)

        self.assertEqual(
            payment.status,
            EcommercePayment.CONFIRMED,
        )
        self.assertEqual(
            payment.provider_status,
            "SUCCESSFUL",
        )
        self.assertEqual(
            payment.provider_reference,
            "MTN-TXN-WPG-001",
        )

        self.assertIsNotNone(
            payment.customer_advance_id
        )

        advance = payment.customer_advance
        advance.refresh_from_db()

        self.assertEqual(
            advance.amount,
            Decimal("200.00"),
        )
        self.assertEqual(
            advance.available_amount,
            Decimal("200.00"),
        )
        self.assertEqual(
            advance.status,
            advance.AVAILABLE,
        )

        self.assertEqual(
            self.order.payment_status,
            "PAID",
        )
        self.assertEqual(
            self.order.status,
            "CONFIRMED",
        )

        mock_order_confirm.assert_called_once()

        entry = advance.receipt_entry

        self.assertIsNotNone(entry)
        self.assertEqual(
            entry.status,
            JournalEntry.POSTED,
        )
        self.assertTrue(entry.is_balanced)

        lines = {
            line.account.code: line
            for line in entry.lines.select_related("account")
        }

        self.assertEqual(
            lines["1120"].debit,
            Decimal("200.00"),
        )
        self.assertEqual(
            lines["1120"].credit,
            Decimal("0.00"),
        )

        self.assertEqual(
            lines["2100"].debit,
            Decimal("0.00"),
        )
        self.assertEqual(
            lines["2100"].credit,
            Decimal("200.00"),
        )


    @patch(
        "ecommerce.services.payment_service.EventEngine.dispatch"
    )
    @patch(
        "ecommerce.services.payment_service.PaymentGatewayRegistry.get"
    )
    def test_mtn_pending_does_not_confirm_payment(
        self,
        mock_gateway_get,
        unused_dispatch,
    ):
        gateway = MagicMock()

        gateway.get_payment_status.return_value = GatewayResult(
            successful=True,
            provider_status="PENDING",
            provider_request_id=self.payment.provider_request_id,
            raw_response={
                "status": "PENDING",
                "amount": "200.00",
                "currency": "RWF",
            },
        )

        mock_gateway_get.return_value = gateway

        payment, changed = (
            EcommercePaymentService.check_provider_status(
                payment=self.payment,
            )
        )

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertFalse(changed)

        self.assertEqual(
            payment.status,
            EcommercePayment.PENDING,
        )
        self.assertEqual(
            payment.provider_status,
            "PENDING",
        )
        self.assertIsNone(
            payment.customer_advance_id
        )

        self.assertEqual(
            self.order.payment_status,
            "UNPAID",
        )
        self.assertEqual(
            self.order.status,
            "PENDING",
        )

        self.assertFalse(
            JournalEntry.objects.filter(
                source_type="CUSTOMER_ADVANCE_RECEIPT",
            ).exists()
        )


    @patch(
        "ecommerce.services.payment_service.EventEngine.dispatch"
    )
    @patch(
        "ecommerce.services.payment_service.PaymentGatewayRegistry.get"
    )
    def test_mtn_failed_does_not_create_customer_advance(
        self,
        mock_gateway_get,
        unused_dispatch,
    ):
        gateway = MagicMock()

        gateway.get_payment_status.return_value = GatewayResult(
            successful=True,
            provider_status="FAILED",
            provider_request_id=self.payment.provider_request_id,
            message="Customer rejected the MTN MoMo payment.",
            raw_response={
                "status": "FAILED",
                "reason": "Payment rejected",
            },
        )

        mock_gateway_get.return_value = gateway

        payment, changed = (
            EcommercePaymentService.check_provider_status(
                payment=self.payment,
            )
        )

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertTrue(changed)

        self.assertEqual(
            payment.status,
            EcommercePayment.FAILED,
        )
        self.assertEqual(
            payment.provider_status,
            "FAILED",
        )
        self.assertIsNone(
            payment.customer_advance_id
        )

        self.assertEqual(
            self.order.payment_status,
            "UNPAID",
        )
        self.assertEqual(
            self.order.status,
            "PENDING",
        )

        self.assertFalse(
            JournalEntry.objects.filter(
                source_type="CUSTOMER_ADVANCE_RECEIPT",
            ).exists()
        )

    def test_failed_payment_can_be_retried_safely(self):
        retry_key = (
            f"CHECKOUT_PAYMENT_ATTEMPT:"
            f"{self.checkout.pk}:"
            f"MTN_MOMO:"
            f"0788000000"
        )

        old_payment_id = self.payment.pk

        self.payment.status = EcommercePayment.FAILED
        self.payment.failure_reason = "Customer rejected payment."
        self.payment.idempotency_key = retry_key
        self.payment.save(
            update_fields=[
                "status",
                "failure_reason",
                "idempotency_key",
                "updated_at",
            ]
        )

        new_payment, created = (
            EcommercePaymentService.initiate_payment(
                checkout=self.checkout,
                method=EcommercePayment.MOBILE_MONEY,
                provider="MTN_MOMO",
                customer_reference="0788000000",
                idempotency_key=retry_key,
            )
        )

        self.assertTrue(created)

        self.assertNotEqual(
            new_payment.pk,
            old_payment_id,
        )

        self.assertEqual(
            new_payment.status,
            EcommercePayment.INITIATED,
        )

        self.assertEqual(
            new_payment.idempotency_key,
            retry_key,
        )

        self.payment.refresh_from_db()

        self.assertIsNone(
            self.payment.idempotency_key
        )

        # Simulate a browser double-submit using the same key.
        same_payment, created_again = (
            EcommercePaymentService.initiate_payment(
                checkout=self.checkout,
                method=EcommercePayment.MOBILE_MONEY,
                provider="MTN_MOMO",
                customer_reference="0788000000",
                idempotency_key=retry_key,
            )
        )

        self.assertFalse(created_again)

        self.assertEqual(
            same_payment.pk,
            new_payment.pk,
        )

    def test_airtel_payment_cannot_be_confirmed_manually(
        self,
    ):
        self.payment.provider = "AIRTEL_MONEY"
        self.payment.customer_reference = "0738000000"
        self.payment.save(
            update_fields=[
                "provider",
                "customer_reference",
                "updated_at",
            ]
        )

        with self.assertRaisesMessage(
            ValidationError,
            "cannot be confirmed manually",
        ):
            EcommercePaymentService.confirm_payment(
                payment=self.payment,
                provider_reference=(
                    "MANUAL-AIRTEL-REFERENCE"
                ),
            )

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            EcommercePayment.PENDING,
        )
        self.assertIsNone(
            self.payment.customer_advance_id
        )
        self.assertEqual(
            self.order.status,
            "PENDING",
        )
        self.assertEqual(
            self.order.payment_status,
            "UNPAID",
        )

        self.assertFalse(
            JournalEntry.objects.filter(
                source_type=(
                    "CUSTOMER_ADVANCE_RECEIPT"
                ),
            ).exists()
        )

    @patch(
        "finance.services.customer_advance_service.EventEngine.dispatch"
    )
    @patch(
        "ecommerce.services.payment_service.EventEngine.dispatch"
    )
    @patch(
        "ecommerce.services.payment_service.OrderService.confirm"
    )
    @patch(
        "ecommerce.services.payment_service.PaymentGatewayRegistry.get"
    )
    def test_airtel_success_posts_customer_advance(
        self,
        mock_gateway_get,
        mock_order_confirm,
        unused_payment_dispatch,
        unused_finance_dispatch,
    ):
        self.payment.provider = "AIRTEL_MONEY"
        self.payment.customer_reference = "0738000000"
        self.payment.save(
            update_fields=[
                "provider",
                "customer_reference",
                "updated_at",
            ]
        )

        gateway = MagicMock()
        gateway.get_payment_status.return_value = (
            GatewayResult(
                successful=True,
                provider_status="SUCCESSFUL",
                provider_request_id=(
                    self.payment.provider_request_id
                ),
                provider_reference=(
                    "AIRTEL-RW-TXN-001"
                ),
                raw_response={
                    "data": {
                        "transaction": {
                            "status": "TS",
                            "airtel_money_id": (
                                "AIRTEL-RW-TXN-001"
                            ),
                        }
                    }
                },
            )
        )
        mock_gateway_get.return_value = gateway

        def confirm_order(*, order, actor=None):
            order.status = "CONFIRMED"
            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )
            return order, {}

        mock_order_confirm.side_effect = confirm_order

        payment, changed = (
            EcommercePaymentService.check_provider_status(
                payment=self.payment,
            )
        )

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertTrue(changed)
        self.assertEqual(
            payment.status,
            EcommercePayment.CONFIRMED,
        )
        self.assertEqual(
            payment.provider_status,
            "SUCCESSFUL",
        )
        self.assertEqual(
            payment.provider_reference,
            "AIRTEL-RW-TXN-001",
        )
        self.assertIsNotNone(
            payment.customer_advance_id
        )

        self.assertEqual(
            self.order.status,
            "CONFIRMED",
        )
        self.assertEqual(
            self.order.payment_status,
            "PAID",
        )

        advance = payment.customer_advance
        advance.refresh_from_db()

        self.assertEqual(
            advance.amount,
            Decimal("200.00"),
        )
        self.assertEqual(
            advance.available_amount,
            Decimal("200.00"),
        )

        entry = advance.receipt_entry

        self.assertIsNotNone(entry)
        self.assertEqual(
            entry.status,
            JournalEntry.POSTED,
        )
        self.assertTrue(entry.is_balanced)

        lines = {
            line.account.code: line
            for line in entry.lines.select_related(
                "account"
            )
        }

        self.assertEqual(
            lines["1120"].debit,
            Decimal("200.00"),
        )
        self.assertEqual(
            lines["2100"].credit,
            Decimal("200.00"),
        )

    @patch(
        "ecommerce.views.EcommercePaymentService"
        ".check_provider_status"
    )
    def test_valid_signed_callback_checks_provider(
        self,
        mock_status_check,
    ):
        mock_status_check.return_value = (
            self.payment,
            False,
        )

        token = signing.dumps(
            {
                "payment_id": self.payment.pk,
                "provider": self.payment.provider,
            },
            salt=(
                "ecommerce.payment."
                "provider-callback.v1"
            ),
            compress=True,
        )

        callback_url = reverse(
            "ecommerce:payment_provider_callback",
            kwargs={"token": token},
        )

        response = self.client.post(
            callback_url,
            data={},
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertTrue(
            response.json()["accepted"]
        )

        mock_status_check.assert_called_once()

        self.payment.refresh_from_db()

        self.assertIsNotNone(
            self.payment.callback_received_at
        )

    @patch(
        "ecommerce.views.EcommercePaymentService"
        ".check_provider_status"
    )
    def test_invalid_callback_token_is_rejected(
        self,
        mock_status_check,
    ):
        callback_url = reverse(
            "ecommerce:payment_provider_callback",
            kwargs={
                "token": "invalid-callback-token",
            },
        )

        response = self.client.post(
            callback_url,
            data={},
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        mock_status_check.assert_not_called()

        self.payment.refresh_from_db()

        self.assertIsNone(
            self.payment.callback_received_at
        )

    @patch(
        "ecommerce.views.EcommercePaymentService"
        ".check_provider_status"
    )
    def test_callback_cannot_target_another_provider(
        self,
        mock_status_check,
    ):
        token = signing.dumps(
            {
                "payment_id": self.payment.pk,
                "provider": "AIRTEL_MONEY",
            },
            salt=(
                "ecommerce.payment."
                "provider-callback.v1"
            ),
            compress=True,
        )

        callback_url = reverse(
            "ecommerce:payment_provider_callback",
            kwargs={"token": token},
        )

        response = self.client.post(
            callback_url,
            data={},
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        mock_status_check.assert_not_called()

class EcommercePaymentReconciliationCommandTests(
    TestCase
):
    def setUp(self):
        self.checkout = EcommerceCheckout.objects.create(
            status="ORDERED",
            customer_name="Reconciliation Customer",
            customer_phone="0788000000",
            currency="RWF",
            subtotal=Decimal("500.00"),
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
        )

        self.payment = EcommercePayment.objects.create(
            checkout=self.checkout,
            method=EcommercePayment.MOBILE_MONEY,
            provider="MTN_MOMO",
            amount=Decimal("500.00"),
            currency="RWF",
            customer_reference="0788000000",
            status=EcommercePayment.PENDING,
            provider_request_id=(
                "22222222-3333-4444-8555-666666666666"
            ),
        )

    @patch(
        "ecommerce.management.commands."
        "reconcile_ecommerce_payments."
        "EcommercePaymentService.check_provider_status"
    )
    def test_dry_run_does_not_contact_provider(
        self,
        mock_status_check,
    ):
        output = StringIO()

        call_command(
            "reconcile_ecommerce_payments",
            dry_run=True,
            min_age=0,
            limit=10,
            stdout=output,
        )

        mock_status_check.assert_not_called()

        self.assertIn(
            "DRY RUN: 1 payment(s) would be checked.",
            output.getvalue(),
        )
        self.assertIn(
            self.payment.payment_number,
            output.getvalue(),
        )

    @patch(
        "ecommerce.management.commands."
        "reconcile_ecommerce_payments."
        "EcommercePaymentService.check_provider_status"
    )
    def test_pending_payment_is_checked(
        self,
        mock_status_check,
    ):
        mock_status_check.return_value = (
            self.payment,
            False,
        )

        output = StringIO()

        call_command(
            "reconcile_ecommerce_payments",
            min_age=0,
            limit=10,
            stdout=output,
        )

        mock_status_check.assert_called_once()

        called_payment = (
            mock_status_check.call_args
            .kwargs["payment"]
        )

        self.assertEqual(
            called_payment.pk,
            self.payment.pk,
        )
        self.assertIn(
            "checked=1",
            output.getvalue(),
        )
        self.assertIn(
            "pending=1",
            output.getvalue(),
        )

    @patch(
        "ecommerce.management.commands."
        "reconcile_ecommerce_payments."
        "EcommercePaymentService.check_provider_status"
    )
    def test_terminal_payment_is_not_checked(
        self,
        mock_status_check,
    ):
        self.payment.status = EcommercePayment.CONFIRMED
        self.payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        output = StringIO()

        call_command(
            "reconcile_ecommerce_payments",
            min_age=0,
            limit=10,
            stdout=output,
        )

        mock_status_check.assert_not_called()

        self.assertIn(
            "No pending Ecommerce payments",
            output.getvalue(),
        )