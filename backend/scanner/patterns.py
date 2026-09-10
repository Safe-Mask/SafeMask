import re


EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9._%+-]{0,62}[A-Za-z0-9])?@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}"
)

PHONE_PATTERN = re.compile(
    r"(?:\+55[\s-]?)?(?:\([1-9]\d\)|[1-9]\d)[\s-]?"
    r"(?:9?\d{4})[-\s]?\d{4}"
)


def normalize_phone(phone: str) -> str | None:
    normalized_phone = phone.strip()
    if not PHONE_PATTERN.fullmatch(normalized_phone):
        return None

    digits = re.sub(r"\D", "", normalized_phone)
    return digits[2:] if normalized_phone.startswith("+55") else digits
