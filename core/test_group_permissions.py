from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from unittest.mock import patch

from .models import Feature, RoleFeature
from .permissions import PermissionService
from .services import CoreSetupService


class GroupPermissionServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="permissions@example.com",
            username="permissions-user",
            first_name="Permission",
            last_name="Tester",
            password="Strong-Test-Password-2026!",
        )
        self.group = Group.objects.create(name="Dynamic Inventory Role")
        self.user.groups.add(self.group)

    def test_native_group_permission_grants_configured_feature(self):
        permission = Permission.objects.get(
            content_type__app_label="inventory",
            codename="view_product",
        )
        self.group.permissions.add(permission)
        Feature.objects.create(
            name="Products",
            code="TEST_INVENTORY_PRODUCTS",
            view_permission="inventory.view_product",
        )

        self.assertTrue(
            PermissionService.user_can_access_feature(
                self.user,
                "TEST_INVENTORY_PRODUCTS",
                "view",
            )
        )

    def test_configured_native_permission_is_authoritative(self):
        feature = Feature.objects.create(
            name="Protected products",
            code="TEST_PROTECTED_PRODUCTS",
            view_permission="inventory.view_product",
        )
        RoleFeature.objects.create(
            role=self.group,
            feature=feature,
            can_view=True,
        )

        self.assertFalse(
            PermissionService.user_can_access_feature(
                self.user,
                feature.code,
                "view",
            )
        )

    def test_legacy_role_feature_remains_available_when_not_configured(self):
        feature = Feature.objects.create(
            name="Legacy feature",
            code="TEST_LEGACY_FEATURE",
        )
        RoleFeature.objects.create(
            role=self.group,
            feature=feature,
            can_view=True,
        )

        self.assertTrue(
            PermissionService.user_can_access_feature(
                self.user,
                feature.code,
                "view",
            )
        )

    def test_all_defaults_allow_explicit_feature_override(self):
        manager = Group.objects.create(name="Override Manager")
        feature = Feature.objects.create(
            name="Expense Requests",
            code="TEST_EXPENSE_REQUEST_OVERRIDE",
            view_permission="finance.view_expenserequest",
            change_permission="finance.change_expenserequest",
        )
        config = {
            "Override Manager": {
                "ALL": {"view": True, "add": False, "edit": False, "delete": False, "approve": False},
                feature.code: {"view": True, "edit": True},
            }
        }
        with patch.dict("core.services.ROLE_FEATURES", config, clear=True):
            CoreSetupService.sync_role_features()
        role_feature = RoleFeature.objects.get(role=manager, feature=feature)
        self.assertTrue(role_feature.can_view)
        self.assertTrue(role_feature.can_edit)
        self.assertTrue(manager.permissions.filter(codename="change_expenserequest").exists())
