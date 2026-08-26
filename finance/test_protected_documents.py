import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from finance.models import IncomeDeclaration


class FinanceProtectedDocumentTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)

        self.owner = get_user_model().objects.create_user(
            username="document-owner",
            email="document-owner@example.com",
            first_name="Document",
            last_name="Owner",
            password="Strong-Test-Password-2026",
        )
        self.outsider = get_user_model().objects.create_user(
            username="document-outsider",
            email="document-outsider@example.com",
            first_name="Document",
            last_name="Outsider",
            password="Strong-Test-Password-2026",
        )
        permission = Permission.objects.get(
            content_type__app_label="finance",
            codename="view_incomedeclaration",
        )
        self.owner.user_permissions.add(permission)
        self.outsider.user_permissions.add(permission)
        self.declaration = IncomeDeclaration.objects.create(
            recorded_by=self.owner,
            business_unit="SHARED",
            title="Protected receipt",
            source_type="OTHER",
            amount="100.00",
            receipt_method="cash",
            receipt_date=timezone.localdate(),
            reference="PROTECTED-001",
            proof_document=SimpleUploadedFile(
                "receipt.pdf",
                b"protected-finance-document",
                content_type="application/pdf",
            ),
        )

    def test_owner_can_download_document_through_protected_route(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse(
                "finance:income_declaration_document",
                kwargs={"pk": self.declaration.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertEqual(
            b"".join(response.streaming_content),
            b"protected-finance-document",
        )

    def test_unrelated_user_cannot_download_document(self):
        self.client.force_login(self.outsider)
        response = self.client.get(
            reverse(
                "finance:income_declaration_document",
                kwargs={"pk": self.declaration.pk},
            )
        )

        self.assertEqual(response.status_code, 403)
