import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from orders.models import Order, OrderItem


class OrderProtectedAttachmentTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)

        self.user = get_user_model().objects.create_user(
            username="order-document-viewer",
            email="order-document-viewer@example.com",
            first_name="Order",
            last_name="Viewer",
            password="Strong-Test-Password-2026",
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="orders",
                codename="view_order",
            )
        )
        order = Order.objects.create(
            user=self.user,
            business_unit="FURNITURE",
            order_type="CUSTOM_FURNITURE",
            customer_name="Protected Customer",
            customer_phone="0788000000",
        )
        self.item = OrderItem.objects.create(
            order=order,
            product_name="Custom bed",
            quantity=1,
            design_attachment=SimpleUploadedFile(
                "bed-design.pdf",
                b"protected-order-design",
                content_type="application/pdf",
            ),
        )

    def test_authorized_user_downloads_attachment_through_view(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "orders:order_item_attachment",
                kwargs={"pk": self.item.pk, "kind": "design"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertEqual(
            b"".join(response.streaming_content),
            b"protected-order-design",
        )

    def test_missing_attachment_type_returns_not_found(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse(
                "orders:order_item_attachment",
                kwargs={"pk": self.item.pk, "kind": "unknown"},
            )
        )

        self.assertEqual(response.status_code, 404)
