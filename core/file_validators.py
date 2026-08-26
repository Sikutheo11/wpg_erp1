from pathlib import Path
import zipfile

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible


IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
DOCUMENT_EXTENSIONS = (
    "pdf", *IMAGE_EXTENSIONS, "doc", "docx", "xls", "xlsx"
)

MIME_TYPES = {
    "pdf": {"application/pdf"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png": {"image/png"},
    "webp": {"image/webp"},
    "doc": {"application/msword"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    "xls": {"application/vnd.ms-excel"},
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    },
}


@deconstructible
class SecureFileValidator:
    def __init__(self, allowed_extensions, max_size_mb):
        self.allowed_extensions = tuple(allowed_extensions)
        self.max_size_mb = max_size_mb
        self.extension_validator = FileExtensionValidator(
            allowed_extensions=self.allowed_extensions
        )

    def __call__(self, value):
        self.extension_validator(value)
        size = getattr(value, "size", None)
        max_bytes = self.max_size_mb * 1024 * 1024
        if size is not None and size > max_bytes:
            raise ValidationError(
                f"File must not exceed {self.max_size_mb} MB."
            )

        extension = Path(value.name).suffix.lower().lstrip(".")
        content_type = getattr(value, "content_type", "") or getattr(
            getattr(value, "file", value),
            "content_type",
            "",
        )
        allowed_mime = MIME_TYPES.get(extension, set())
        if (
            content_type
            and content_type != "application/octet-stream"
            and allowed_mime
            and content_type.lower() not in allowed_mime
        ):
            raise ValidationError(
                "The file content type does not match its extension."
            )

        self._validate_signature(value, extension)

    @staticmethod
    def _validate_signature(value, extension):
        stream = getattr(value, "file", value)
        try:
            position = stream.tell()
            stream.seek(0)
            header = stream.read(16)
            stream.seek(0)

            valid = {
                "pdf": header.startswith(b"%PDF-"),
                "jpg": header.startswith(b"\xff\xd8\xff"),
                "jpeg": header.startswith(b"\xff\xd8\xff"),
                "png": header.startswith(b"\x89PNG\r\n\x1a\n"),
                "webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
                "doc": header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
                "xls": header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
            }
            if extension in {"docx", "xlsx"}:
                valid[extension] = SecureFileValidator._valid_office_zip(
                    stream,
                    extension,
                )
            if not valid.get(extension, False):
                raise ValidationError(
                    "File contents do not match the selected file type."
                )
        except (AttributeError, OSError, zipfile.BadZipFile):
            raise ValidationError("The uploaded file could not be verified.")
        finally:
            try:
                stream.seek(position)
            except (AttributeError, OSError, UnboundLocalError):
                pass

    @staticmethod
    def _valid_office_zip(stream, extension):
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            names = set(archive.namelist())
        required_folder = "word/" if extension == "docx" else "xl/"
        return (
            "[Content_Types].xml" in names
            and any(name.startswith(required_folder) for name in names)
        )


validate_image_upload = SecureFileValidator(
    allowed_extensions=IMAGE_EXTENSIONS,
    max_size_mb=5,
)
validate_finance_proof = SecureFileValidator(
    allowed_extensions=("pdf", *IMAGE_EXTENSIONS),
    max_size_mb=8,
)
validate_business_document = SecureFileValidator(
    allowed_extensions=DOCUMENT_EXTENSIONS,
    max_size_mb=12,
)
