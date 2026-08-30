from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from Employee.models import Department
from inventory.forms import AssetAssignmentForm
from inventory.models import Asset, AssetAssignment, Category, Supplier, Warehouse


class InventorySidebarNavigationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="inventory-sidebar@example.com",
            username="inventory-sidebar",
            first_name="Inventory",
            last_name="Administrator",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)

    def test_inventory_master_tables_render(self):
        for url_name in (
            "inventory:category_list",
            "inventory:warehouse_list",
            "inventory:supplier_list",
            "inventory:asset_assignment_list",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_authorized_user_sees_master_data_actions(self):
        actions = (
            ("inventory:category_list", "inventory:category_create", "Add Category"),
            ("inventory:warehouse_list", "inventory:warehouse_create", "Add Warehouse"),
            ("inventory:supplier_list", "inventory:supplier_create", "Add Supplier"),
            (
                "inventory:asset_assignment_list",
                "inventory:asset_assignment_create",
                "Assign Asset",
            ),
        )
        for list_name, create_name, label in actions:
            with self.subTest(list_name=list_name):
                response = self.client.get(reverse(list_name))
                self.assertContains(response, reverse(create_name))
                self.assertContains(response, label)

    def test_create_and_update_pages_render(self):
        category = Category.objects.create(name="Timber")
        warehouse = Warehouse.objects.create(name="Main Timber Store")
        supplier = Supplier.objects.create(name="Timber Supplier", phone="0788000000")
        department = Department.objects.create(name="Inventory Operations")
        asset = Asset.objects.create(
            asset_type="machine",
            name="Planer",
            purchase_cost="500000.00",
            purchase_date="2026-08-26",
        )
        assignment = AssetAssignment.objects.create(
            asset=asset,
            department=department,
            assigned_date="2026-08-26",
        )
        urls = (
            reverse("inventory:category_create"),
            reverse("inventory:category_update", args=[category.pk]),
            reverse("inventory:warehouse_create"),
            reverse("inventory:warehouse_update", args=[warehouse.pk]),
            reverse("inventory:supplier_create"),
            reverse("inventory:supplier_update", args=[supplier.pk]),
            reverse("inventory:asset_assignment_create"),
            reverse("inventory:asset_assignment_update", args=[assignment.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_master_data_can_be_created(self):
        response = self.client.post(
            reverse("inventory:category_create"),
            {"name": "Hardware", "description": "Furniture hardware", "is_active": "on"},
        )
        self.assertRedirects(response, reverse("inventory:category_list"))
        self.assertTrue(Category.objects.filter(name="Hardware").exists())

        response = self.client.post(
            reverse("inventory:warehouse_create"),
            {
                "name": "Finished Goods Store",
                "code": "FGS",
                "warehouse_type": "FINISHED_GOODS",
                "business_unit": "FURNITURE",
                "location": "Rubengera",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("inventory:warehouse_list"))
        warehouse = Warehouse.objects.get(name='Finished Goods Store')
        self.assertTrue(warehouse.code)
        self.assertNotEqual(warehouse.code, "FGS")

        response = self.client.post(
            reverse("inventory:supplier_create"),
            {
                "name": "WPG Timber Partner",
                "phone": "0788000001",
                "email": "supplier@example.com",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("inventory:supplier_list"))
        self.assertTrue(Supplier.objects.filter(name="WPG Timber Partner").exists())

    def test_user_without_add_permission_cannot_open_create_pages(self):
        user = get_user_model().objects.create_user(
            email="inventory-viewer@example.com",
            username="inventory-viewer",
            first_name="Inventory",
            last_name="Viewer",
            password="Strong-Test-Password-2026!",
        )
        group = Group.objects.create(name="Inventory Viewer Only")
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="inventory",
                codename="view_category",
            )
        )
        user.groups.add(group)
        self.client.force_login(user)

        response = self.client.get(reverse("inventory:category_create"))
        self.assertEqual(response.status_code, 403)


class AssetAssignmentFormTests(TestCase):
    def test_return_date_cannot_precede_assignment_date(self):
        department = Department.objects.create(name="Furniture Workshop")
        asset = Asset.objects.create(
            asset_type="tool",
            name="Circular Saw",
            purchase_cost="250000.00",
            purchase_date="2026-08-01",
        )
        form = AssetAssignmentForm(
            data={
                "asset": asset.pk,
                "department": department.pk,
                "assigned_date": "2026-08-26",
                "returned_date": "2026-08-25",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("returned_date", form.errors)
