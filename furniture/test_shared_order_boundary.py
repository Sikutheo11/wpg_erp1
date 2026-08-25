from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.test import TestCase
from django.urls import reverse


class SharedOrderFurnitureBoundaryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="workflow-admin@example.com",
            username="workflow-admin",
            first_name="Workflow",
            last_name="Admin",
            password="Strong-Test-Password-2026!",
        )
        self.client.force_login(self.user)

    def test_legacy_furniture_create_redirects_to_shared_order_engine(self):
        response = self.client.get(reverse("furniture:order_create"))

        self.assertRedirects(
            response,
            reverse("orders:business_unit_select"),
            fetch_redirect_response=False,
        )

    def test_production_job_template_is_not_labelled_customer_order(self):
        source = get_template(
            "furniture/production_job_form.html"
        ).template.source

        self.assertIn("Create Production Job", source)
        self.assertNotIn("Create Customer Order", source)
        self.assertNotIn("Save Order", source)

    def test_production_job_uses_enterprise_order_model(self):
        from furniture.models import ProductionJob
        from orders.models import Order

        related_model = (
            ProductionJob._meta.get_field("order").remote_field.model
        )

        self.assertIs(related_model, Order)
