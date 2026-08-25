from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Customer, Invoice, Sale


class SalesNavigationRegressionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="sales-navigation@example.com",
            username="sales-navigation",
            first_name="Sales",
            last_name="Navigator",
            password="Strong-Test-Password-2026",
        )
        group = Group.objects.create(name="Sales Navigation Testers")
        group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label="sales",
                codename__in=[
                    "view_customer",
                    "add_customer",
                    "change_customer",
                    "delete_customer",
                    "view_salesquotation",
                    "add_salesquotation",
                    "view_sale",
                    "view_invoice",
                    "view_customerpayment",
                ],
            )
        )
        self.user.groups.add(group)
        self.client.force_login(self.user)

        self.customer = Customer.objects.create(
            customer_type="COMPANY",
            company_name="Navigation Customer",
            phone="+250788000001",
        )
        self.sale = Sale.objects.create(
            customer=self.customer,
            sale_no="SALE-NAV-001",
            total_amount=Decimal("1250.00"),
        )
        self.invoice = Invoice.objects.create(
            sale=self.sale,
            invoice_no="INV-NAV-001",
            due_date=timezone.localdate() + timedelta(days=30),
            total_amount=Decimal("1250.00"),
        )

    def test_sales_register_pages_render_real_templates(self):
        urls = [
            reverse("sales:customer_list"),
            reverse("sales:customer_create"),
            reverse("sales:customer_detail", kwargs={"pk": self.customer.pk}),
            reverse("sales:customer_update", kwargs={"pk": self.customer.pk}),
            reverse("sales:customer_delete", kwargs={"pk": self.customer.pk}),
            reverse("sales:sale_list"),
            reverse("sales:sale_detail", kwargs={"pk": self.sale.pk}),
            reverse("sales:invoice_list"),
            reverse("sales:invoice_detail", kwargs={"pk": self.invoice.pk}),
            reverse("sales:payment_list"),
            reverse("sales:sales_report"),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_linked_customer_uses_custom_user_full_name(self):
        linked_customer = Customer.objects.create(
            user=self.user,
            phone="+250788000002",
        )

        self.assertEqual(linked_customer.display_name, "Sales Navigator")
