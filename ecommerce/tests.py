from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from agriculture.models import PoultryFarm
from finance.models import JournalEntry, LedgerAccount
from inventory.models import Product
from orders.models import Order, OrderItem

from ecommerce.models import (
    MarketplaceOrderLine,
    MarketplaceSeller,
    OnlineProduct,
    SellerProductAssignment,
    SellerSettlement,
)
from ecommerce.services import (
    MarketplaceCommissionService,
    SellerSettlementService,
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
