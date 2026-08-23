from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from accounts.utils import redirect_by_role
from core.models import EnterpriseEngine, Feature, GroupAccessProfile
from core.services import CoreSetupService


class CoreSynchronizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        CoreSetupService.sync_all()

    def test_sync_creates_finance_engine_and_features(self):
        self.assertTrue(
            EnterpriseEngine.objects.filter(
                code="FINANCE",
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            Feature.objects.filter(
                code="FINANCE_DASHBOARD",
                view_permission="finance.view_account",
                is_active=True,
            ).exists()
        )

    def test_sync_replaces_stale_managed_group_permissions(self):
        group = Group.objects.get(name="Finance Manager")

        self.assertTrue(group.permissions.filter(codename="view_account").exists())
        self.assertFalse(
            group.permissions.filter(
                content_type__app_label="inventory",
            ).exists()
        )
        self.assertEqual(
            set(
                group.permissions.filter(
                    content_type__app_label="sales",
                ).values_list("codename", flat=True)
            ),
            {"view_customer"},
        )

    def test_finance_manager_lands_on_finance_dashboard(self):
        group = Group.objects.get(name="Finance Manager")
        profile = GroupAccessProfile.objects.get(group=group)
        self.assertEqual(profile.landing_feature.code, "FINANCE_DASHBOARD")

        user = get_user_model().objects.create_user(
            email="finance.manager@example.com",
            username="finance-manager",
            first_name="Finance",
            last_name="Manager",
            password="Strong-Test-Password-2026",
        )
        user.groups.add(group)

        response = redirect_by_role(user)

        self.assertEqual(response.url, reverse("finance:finance_dashboard"))
