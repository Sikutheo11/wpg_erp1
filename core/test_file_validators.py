from io import BytesIO
import zipfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.file_validators import (
    SecureFileValidator,
    validate_business_document,
    validate_finance_proof,
    validate_image_upload,
)


class SecureFileValidatorTests(SimpleTestCase):
    def test_valid_pdf_is_accepted(self):
        upload = SimpleUploadedFile(
            "receipt.pdf",
            b"%PDF-1.7\nvalid test document",
            content_type="application/pdf",
        )
        validate_finance_proof(upload)

    def test_executable_renamed_as_pdf_is_rejected(self):
        upload = SimpleUploadedFile(
            "receipt.pdf",
            b"MZ executable content",
            content_type="application/pdf",
        )
        with self.assertRaises(ValidationError):
            validate_finance_proof(upload)

    def test_mime_type_must_match_extension(self):
        upload = SimpleUploadedFile(
            "photo.png",
            b"\x89PNG\r\n\x1a\ncontent",
            content_type="text/html",
        )
        with self.assertRaises(ValidationError):
            validate_image_upload(upload)

    def test_disallowed_extension_is_rejected(self):
        upload = SimpleUploadedFile(
            "payload.svg",
            b"<svg><script>alert(1)</script></svg>",
            content_type="image/svg+xml",
        )
        with self.assertRaises(ValidationError):
            validate_business_document(upload)

    def test_size_limit_is_enforced(self):
        validator = SecureFileValidator(("pdf",), max_size_mb=1)
        upload = SimpleUploadedFile(
            "large.pdf",
            b"%PDF-" + (b"0" * (1024 * 1024)),
            content_type="application/pdf",
        )
        with self.assertRaises(ValidationError):
            validator(upload)

    def test_valid_docx_container_is_accepted(self):
        stream = BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("word/document.xml", "<document />")
        upload = SimpleUploadedFile(
            "specification.docx",
            stream.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )
        validate_business_document(upload)
