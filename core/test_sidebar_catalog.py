from django.test import SimpleTestCase
from django.urls import reverse

from core.initial_data import BUSINESS_UNIT_FEATURES, ENGINE_FEATURES


class SidebarCatalogTests(SimpleTestCase):
    def test_every_visible_sidebar_feature_has_a_valid_url(self):
        for section in (BUSINESS_UNIT_FEATURES, ENGINE_FEATURES):
            for owner_code, definitions in section.items():
                for name, code, url_name, icon, order in definitions:
                    with self.subTest(owner=owner_code, feature=code):
                        self.assertTrue(url_name, f"{code} has no sidebar URL")
                        self.assertTrue(reverse(url_name))

    def test_inventory_master_tables_are_registered(self):
        feature_codes = {
            definition[1]
            for definition in ENGINE_FEATURES["INVENTORY"]
        }
        self.assertTrue(
            {
                "INVENTORY_CATEGORIES",
                "INVENTORY_WAREHOUSES",
                "INVENTORY_SUPPLIERS",
                "INVENTORY_PRODUCTS",
                "INVENTORY_RAW_MATERIALS",
                "INVENTORY_STOCK_MOVEMENTS",
            }.issubset(feature_codes)
        )
