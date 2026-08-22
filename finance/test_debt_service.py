from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from finance.models import (
    Counterparty,
    DebtLine,
    DebtRecord,
)
from inventory.models import (
    Product,
    Asset,
    RawMaterial,
)

from finance.services.debt_service import (
    DebtService,
)



class DebtServiceTests(TestCase):
    def setUp(self):
        self.counterparty = (
            Counterparty.objects.create(
                name="Test Counterparty",
                phone="0788123456",
            )
        )

        self.raw_material = RawMaterial.objects.create(
            name="Pine timber",
            code="RAW-DEBT-001",
            unit="piece",
            unit_cost=Decimal("5000.00"),
        )

        self.asset = Asset.objects.create(
            asset_type="machine",
            name="Wood cutting machine",
            asset_code="AST-DEBT-001",
            purchase_cost=Decimal("750000.00"),
            purchase_date=date(2026, 8, 21),
        )

    def test_create_receivable_debt_with_multiple_lines(self):
        debt = DebtService.create_debt(
            counterparty=self.counterparty,
            direction=DebtRecord.THEY_OWE_US,
            business_unit="FURNITURE",
            lines=[
                {
                    "description": "Chair",
                    "quantity": "2",
                    "unit": "piece",
                    "unit_price": "25000",
                },
                {
                    "description": "Transport",
                    "quantity": "1",
                    "unit": "service",
                    "unit_price": "5000",
                },
            ],
        )

        debt.refresh_from_db()
        self.counterparty.refresh_from_db()

        self.assertEqual(
            debt.lines.count(),
            2,
        )
        self.assertEqual(
            debt.total_amount,
            Decimal("55000.00"),
        )
        self.assertEqual(
            debt.status,
            DebtRecord.OPEN,
        )
        self.assertTrue(
            self.counterparty.is_customer,
        )

    def test_create_payable_marks_counterparty_as_supplier(self):
        debt = DebtService.create_debt(
            counterparty=self.counterparty,
            direction=DebtRecord.WE_OWE_THEM,
            lines=[
                {
                    "description": "Timber supplied",
                    "quantity": "10",
                    "unit": "piece",
                    "unit_price": "3000",
                },
            ],
        )

        self.counterparty.refresh_from_db()

        self.assertEqual(
            debt.total_amount,
            Decimal("30000.00"),
        )
        self.assertTrue(
            self.counterparty.is_supplier,
        )

    def test_debt_requires_at_least_one_line(self):
        with self.assertRaises(ValidationError):
            DebtService.create_debt(
                counterparty=self.counterparty,
                direction=DebtRecord.THEY_OWE_US,
                lines=[],
            )

        self.assertEqual(
            DebtRecord.objects.count(),
            0,
        )

    def test_invalid_line_rolls_back_entire_debt(self):
        with self.assertRaises(ValidationError):
            DebtService.create_debt(
                counterparty=self.counterparty,
                direction=DebtRecord.WE_OWE_THEM,
                lines=[
                    {
                        "description": "Valid line",
                        "quantity": "1",
                        "unit": "piece",
                        "unit_price": "1000",
                    },
                    {
                        "description": "Invalid line",
                        "quantity": "0",
                        "unit": "piece",
                        "unit_price": "1000",
                    },
                ],
            )

        self.assertEqual(
            DebtRecord.objects.count(),
            0,
        )

    def test_zero_total_debt_is_rejected_and_rolled_back(self):
        with self.assertRaises(ValidationError):
            DebtService.create_debt(
                counterparty=self.counterparty,
                direction=DebtRecord.THEY_OWE_US,
                lines=[
                    {
                        "description": "Zero value",
                        "quantity": "1",
                        "unit": "service",
                        "unit_price": "0",
                    },
                ],
            )

        self.assertEqual(
            DebtRecord.objects.count(),
            0,
        )

    def test_inactive_counterparty_is_rejected(self):
        self.counterparty.is_active = False
        self.counterparty.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        with self.assertRaises(ValidationError):
            DebtService.create_debt(
                counterparty=self.counterparty,
                direction=DebtRecord.THEY_OWE_US,
                lines=[
                    {
                        "description": "Service",
                        "quantity": "1",
                        "unit": "service",
                        "unit_price": "1000",
                    },
                ],
            )

        self.assertEqual(
            DebtRecord.objects.count(),
            0,
        )
    
    def test_create_debt_with_raw_material_line(self):
        debt = DebtService.create_debt(
            counterparty=self.counterparty,
            direction=DebtRecord.WE_OWE_THEM,
            business_unit="FURNITURE",
            lines=[
                {
                    "item_type": DebtLine.RAW_MATERIAL,
                    "raw_material": self.raw_material,
                    "quantity": "12",
                    "unit": "piece",
                    "unit_price": "5000",
                },
            ],
        )

        debt.refresh_from_db()
        line = debt.lines.get()

        self.assertEqual(
            line.item_type,
            DebtLine.RAW_MATERIAL,
        )
        self.assertEqual(
            line.raw_material,
            self.raw_material,
        )
        self.assertIsNone(line.product)
        self.assertIsNone(line.asset)
        self.assertEqual(
            line.description,
            "Pine timber",
        )
        self.assertEqual(
            line.line_total,
            Decimal("60000.00"),
        )
        self.assertEqual(
            debt.total_amount,
            Decimal("60000.00"),
        )

    def test_create_debt_with_asset_line(self):
        debt = DebtService.create_debt(
            counterparty=self.counterparty,
            direction=DebtRecord.WE_OWE_THEM,
            business_unit="GENERAL",
            lines=[
                {
                    "item_type": DebtLine.ASSET,
                    "asset": self.asset,
                    "quantity": "1",
                    "unit": "machine",
                    "unit_price": "750000",
                },
            ],
        )

        debt.refresh_from_db()
        line = debt.lines.get()

        self.assertEqual(
            line.item_type,
            DebtLine.ASSET,
        )
        self.assertEqual(
            line.asset,
            self.asset,
        )
        self.assertIsNone(line.product)
        self.assertIsNone(line.raw_material)
        self.assertEqual(
            line.description,
            "Wood cutting machine",
        )
        self.assertEqual(
            debt.total_amount,
            Decimal("750000.00"),
        )

    def test_service_line_requires_description(self):
        with self.assertRaises(ValidationError):
            DebtService.create_debt(
                counterparty=self.counterparty,
                direction=DebtRecord.THEY_OWE_US,
                lines=[
                    {
                        "item_type": DebtLine.SERVICE,
                        "description": "",
                        "quantity": "1",
                        "unit": "service",
                        "unit_price": "10000",
                    },
                ],
            )

        self.assertEqual(
            DebtRecord.objects.count(),
            0,
        )

    def test_item_type_cannot_use_wrong_source(self):
        with self.assertRaises(ValidationError):
            DebtService.create_debt(
                counterparty=self.counterparty,
                direction=DebtRecord.WE_OWE_THEM,
                lines=[
                    {
                        "item_type": DebtLine.ASSET,
                        "raw_material": self.raw_material,
                        "quantity": "1",
                        "unit": "piece",
                        "unit_price": "5000",
                    },
                ],
            )

        self.assertEqual(
            DebtRecord.objects.count(),
            0,
        )
