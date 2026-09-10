import re


EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9._%+-]{0,62}[A-Za-z0-9])?@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}"
)

PHONE_PATTERN = re.compile(
    r"(?:\+55[\s-]?)?(?:\([1-9]\d\)|[1-9]\d)[\s-]?"
    r"(?:9?\d{4})[-\s]?\d{4}"
)

CPF_PATTERN = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
CNS_PATTERN = re.compile(r"\b\d{15}\b")
CID10_PATTERN = re.compile(r"\b[A-TV-Z]\d{2}(?:\.\d{1,4})?\b", re.IGNORECASE)
CRM_PATTERN = re.compile(r"CRM(?:\s*[-/]\s*[A-Z]{2})?\s+\d{4,6}", re.IGNORECASE)


def normalize_phone(phone: str) -> str | None:
    normalized_phone = phone.strip()
    if not PHONE_PATTERN.fullmatch(normalized_phone):
        return None

    digits = re.sub(r"\D", "", normalized_phone)
    return digits[2:] if normalized_phone.startswith("+55") else digits


def mask_phone(phone: str) -> str | None:
    """Oculta o miolo do telefone sem alterar sua formatação original."""
    normalized_phone = phone.strip()
    if not PHONE_PATTERN.fullmatch(normalized_phone):
        return None

    digit_positions = [
        index for index, character in enumerate(normalized_phone) if character.isdigit()
    ]
    prefix_length = 4 if normalized_phone.startswith("+55") else 2
    visible_positions = set(digit_positions[:prefix_length] + digit_positions[-4:])

    return "".join(
        character
        if not character.isdigit() or index in visible_positions
        else "*"
        for index, character in enumerate(normalized_phone)
    )


def mask_cpf(cpf: str) -> str | None:
    if not CPF_PATTERN.fullmatch(cpf):
        return None

    return "***.***.***-**"


def increment_cpf_count(current_count: int, entity_type: str, occurrences: int) -> int:
    return current_count + occurrences if entity_type == "CPF" else current_count
