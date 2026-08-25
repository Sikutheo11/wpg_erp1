from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


class TemplateShellArchitectureTests(TestCase):
    def test_no_page_extends_legacy_base(self):
        templates = Path(settings.BASE_DIR, "templates")
        offenders = []

        for template in templates.rglob("*.html"):
            if template.name == "base.html":
                continue
            source = template.read_text(encoding="utf-8")
            if "extends \"base.html\"" in source or "extends 'base.html'" in source:
                offenders.append(str(template.relative_to(templates)))

        self.assertEqual(offenders, [])

    def test_customer_login_landing_is_marketplace(self):
        User = get_user_model()
        customer = User.objects.create_user(
            username="shell.customer@test.local",
            email="shell.customer@test.local",
            password="test-password",
            first_name="Shell",
            last_name="Customer",
        )
        customer_group, unused_created = Group.objects.get_or_create(
            name="Customer"
        )
        customer.groups.add(customer_group)

        self.client.force_login(customer)
        response = self.client.get(reverse("core:customer_dashboard"))

        self.assertRedirects(
            response,
            reverse("ecommerce:shop"),
            fetch_redirect_response=False,
        )

    def test_marketplace_management_pages_use_staff_shell(self):
        templates = Path(settings.BASE_DIR, "templates", "ecommerce")
        management_templates = [
            templates / "payments" / "payment_refund.html",
            templates / "reports" / "marketplace_report.html",
            *templates.glob("sellers/*.html"),
            *templates.glob("settlements/*.html"),
        ]

        for template in management_templates:
            with self.subTest(template=template.name):
                source = template.read_text(encoding="utf-8")
                self.assertIn('extends "base_dashboard.html"', source)
