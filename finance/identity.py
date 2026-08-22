import re

from django.core.exceptions import ValidationError


def normalize_rwanda_phone(value):
    """
    Return a canonical Rwanda phone number and its identity key.

    These inputs identify the same number:
    0788123456
    +250788123456
    250788123456
    788123456

    Result:
    ("+250788123456", "788123456")
    """
    digits = re.sub(
        r"\D",
        "",
        str(value or ""),
    )

    if digits.startswith("250") and len(digits) == 12:
        national_number = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        national_number = digits[1:]
    elif len(digits) == 9:
        national_number = digits
    else:
        raise ValidationError(
            {
                "phone": (
                    "Enter a valid Rwanda telephone number, "
                    "for example 0788123456 or +250788123456."
                )
            }
        )

    if len(national_number) != 9:
        raise ValidationError(
            {"phone": "The telephone number must contain 9 national digits."}
        )

    return (
        f"+250{national_number}",
        national_number,
    )


def normalize_bank_account(value):
    """
    Normalize a bank account for reliable duplicate detection.

    Spaces, hyphens and other separators are ignored.
    Letters are converted to uppercase.
    """
    normalized = re.sub(
        r"[^0-9A-Za-z]",
        "",
        str(value or ""),
    ).upper()

    return normalized or None