from django import forms
from django.test import TestCase

from agriculture.models import PoultryBreed, PoultryFarm, PoultryHouse
from Employee.models import Department, Employee
from inventory.models import Asset, Product, RawMaterial, Warehouse

from core.internal_codes import (
    assign_missing_internal_codes,
    install_model_form_code_policy,
    internal_code_fields_for_model,
)


class SystemwideInternalCodePolicyTests(TestCase):
    def setUp(self):
        install_model_form_code_policy()

    def test_known_internal_code_fields_are_detected(self):
        expected = {
            Warehouse: {"code"},
            RawMaterial: {"code"},
            Product: {"product_code"},
            Asset: {"asset_code"},
            Department: {"code"},
            Employee: {"employee_code"},
            PoultryFarm: {"code"},
            PoultryHouse: {"code"},
            PoultryBreed: {"code"},
        }
        for model, expected_fields in expected.items():
            with self.subTest(model=model._meta.label):
                detected = {
                    field.name for field in internal_code_fields_for_model(model)
                }
                self.assertTrue(expected_fields.issubset(detected))

    def test_model_form_code_fields_are_hidden_disabled_and_optional(self):
        for model in (Warehouse, RawMaterial, Product, Department, PoultryFarm, PoultryBreed):
            code_fields = internal_code_fields_for_model(model)
            if not code_fields:
                continue
            field_names = [field.name for field in code_fields]
            FormClass = forms.modelform_factory(model, fields=field_names)
            form = FormClass()
            for field_name in field_names:
                with self.subTest(model=model._meta.label, field=field_name):
                    field = form.fields[field_name]
                    self.assertIsInstance(field.widget, forms.HiddenInput)
                    self.assertTrue(field.disabled)
                    self.assertFalse(field.required)

    def test_missing_code_is_generated_and_existing_code_is_preserved(self):
        warehouse = Warehouse(name="Main Store")
        assign_missing_internal_codes(warehouse)
        self.assertTrue(warehouse.code)
        self.assertTrue(warehouse.code.startswith("WH-"))

        existing = Warehouse(name="Second Store", code="KEEP-ME")
        assign_missing_internal_codes(existing)
        self.assertEqual(existing.code, "KEEP-ME")

        product = Product(
            name="Office Desk",
            business_unit="FURNITURE",
            product_type="FINISHED_GOOD",
        )
        assign_missing_internal_codes(product)
        self.assertTrue(product.product_code.startswith("FUR-PRD-"))

    def test_external_identifiers_are_not_internal_codes(self):
        names = {field.name for field in internal_code_fields_for_model(Product)}
        self.assertNotIn("barcode", names)
