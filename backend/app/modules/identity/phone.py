"""Constrained Iranian mobile normalization for the domestic MVP."""

import re


class InvalidPhoneNumber(ValueError):
    pass


_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_SEPARATORS = re.compile(r"[\s().-]+")


def normalize_iranian_mobile(value: str) -> str:
    if not isinstance(value, str) or len(value) > 40:
        raise InvalidPhoneNumber("unsupported phone number")
    normalized = value.translate(_DIGITS).strip()
    if any(char.isalpha() for char in normalized) or "/" in normalized:
        raise InvalidPhoneNumber("unsupported phone number")
    normalized = _SEPARATORS.sub("", normalized)
    if normalized.startswith("0098"):
        normalized = "+" + normalized[2:]
    if normalized.startswith("+98"):
        national = normalized[3:]
    elif normalized.startswith("09"):
        national = normalized[1:]
    elif normalized.startswith("9"):
        # A country code is never inferred from a bare national number.
        raise InvalidPhoneNumber("explicit country or domestic prefix required")
    else:
        raise InvalidPhoneNumber("unsupported country or number format")
    if len(national) != 10 or not national.startswith("9") or not national.isascii() or not national.isdigit():
        raise InvalidPhoneNumber("not a supported Iranian mobile number")
    return "+98" + national
