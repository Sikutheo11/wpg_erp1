from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from Employee.models import Department, Employee
from inventory.forms import AssetAssignmentForm, RawMaterialForm, WarehouseForm
from inventory.models import Asset, AssetAssignment, Category, RawMaterial


class InventoryResourceFormUxTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="inventory-resource-admin",
            email="inventory-resource-admin@example.com",
            first_name="Inventory",
            last_name="Resource Admin",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)

    def test_material_form_includes_category_and_stock_controls(self):
        form = RawMaterialForm()
        for field_name in (
            "category",
            "supplier",
            "unit",
            "minimum_stock",
            "unit_cost",
        ):
            self.assertIn(field_name, form.fields)

    def test_material_create_detail_and_update_pages_render(self):
        category = Category.objects.create(name="Timber Material")
        material = RawMaterial.objects.create(
            category=category,
            name="Pine Timber",
            code="TIM-PINE-UX",
            unit="piece",
            minimum_stock="10",
            unit_cost="15000",
        )
        for url in (
            reverse("inventory:material_create"),
            reverse("inventory:material_detail", args=[material.pk]),
            reverse("inventory:material_update", args=[material.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_asset_update_page_and_list_action_render(self):
        asset = Asset.objects.create(
            asset_type="machine",
            name="Workshop Planer",
            purchase_cost="750000",
            purchase_date="2026-08-26",
        )
        response = self.client.get(
            reverse("inventory:asset_update", args=[asset.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save Changes")
        response = self.client.get(reverse("inventory:asset_list"))
        self.assertContains(
            response,
            reverse("inventory:asset_update", args=[asset.pk]),
        )

    def test_active_assignment_hides_asset_from_new_assignment(self):
        department = Department.objects.create(name="Furniture Asset Custody")
        asset = Asset.objects.create(
            asset_type="tool",
            name="Assigned Drill",
            purchase_cost="120000",
            purchase_date="2026-08-26",
        )
        AssetAssignment.objects.create(
            asset=asset,
            department=department,
            assigned_date="2026-08-26",
        )
        form = AssetAssignmentForm()
        self.assertNotIn(asset, form.fields["asset"].queryset)

    def test_assignment_employee_must_match_department(self):
        department = Department.objects.create(name="Furniture Workshop UX")
        other_department = Department.objects.create(name="Construction UX")
        employee_user = get_user_model().objects.create_user(
            username="asset-employee",
            email="asset-employee@example.com",
            first_name="Asset",
            last_name="Employee",
            password="Strong-Test-Password-2026!",
        )
        employee = Employee.objects.create(
            user=employee_user,
            department=other_department,
            national_id="1199980012345678",
            emergency_contact="0788000000",
        )
        asset = Asset.objects.create(
            asset_type="tool",
            name="Available Drill",
            purchase_cost="100000",
            purchase_date="2026-08-26",
        )
        form = AssetAssignmentForm(data={
            "asset": asset.pk,
            "department": department.pk,
            "employee": employee.pk,
            "assigned_date": "2026-08-26",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("employee", form.errors)

    def test_warehouse_code_is_optional(self):
        form = WarehouseForm(data={
            "name": "Furniture Finished Goods",
            "warehouse_type": "FINISHED_GOODS",
            "business_unit": "FURNITURE",
            "location": "Rubengera",
            "is_active": "on",
        })
        self.assertTrue(form.is_valid(), form.errors)
        warehouse = form.save()
        self.assertTrue(warehouse.code)
