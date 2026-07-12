from __future__ import annotations

import unicodedata


def normalize_identity_value(identity_type: str, value: str) -> str:
    if identity_type == "email":
        return unicodedata.normalize("NFC", value).strip().casefold()
    if identity_type == "student_no":
        return unicodedata.normalize("NFC", value).strip()
    if identity_type == "phone":
        return normalize_phone(value)
    return unicodedata.normalize("NFC", value).strip()


def normalize_phone(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip()
    compact = "".join(char for char in normalized if char not in " -().")
    if compact.startswith("00"):
        compact = f"+{compact[2:]}"
    if not compact.startswith("+"):
        raise ValueError("phone identity must use an international calling code")
    digits = compact[1:]
    if not digits.isdigit() or len(digits) < 8 or len(digits) > 15 or digits[0] == "0":
        raise ValueError("phone identity is not E.164 compatible")
    return f"+{digits}"
