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

# Deteccao de telefone no texto. PHONE_PATTERN (acima) confere um telefone ja
# isolado (mascara, normalizacao); para achar telefone no meio do texto ele
# casava numeros longos sem separador (protocolo, codigo de barras). Aqui o
# telefone exige DDD e separador: DDD entre parenteses ou seguido de espaco ou
# hifen, ou hifen antes dos quatro ultimos digitos. Ponto ou virgula depois do
# numero so barram quando seguidos de digito: no fim da frase, vale.
_FIM_TELEFONE = r"(?!\d)(?![.,]\d)"
PHONE_DETECTION_PATTERN = re.compile(
    r"(?<![\d.])(?:\+55[\s-]?)?(?:\(\d{2}\)\s?|\d{2}[\s-])9?\d{4}-?\d{4}" + _FIM_TELEFONE
    + r"|(?<![\d.])(?:\+55[\s-]?)?\d{2}9?\d{4}-\d{4}" + _FIM_TELEFONE
)

# RG: formato com pontos (12.345.678-9) ou numero depois de um rotulo ("RG",
# "R.G.", "identidade", "registro geral"). O padrao anterior aceitava qualquer
# sequencia de 7 a 9 digitos e pegava trechos de processo, protocolo e CEP. O
# grupo `valor...` e so o numero: a tarja nao cobre o rotulo. O orgao emissor
# depois do numero ("-SSP", " SSP/DF") e aceito e fica fora da tarja.
_FIM_RG = r"(?!\d)(?![.,/\-]\d)"
RG_PATTERN = re.compile(
    r"(?P<valor>(?<![\d.$])\d{1,2}\.\d{3}\.\d{3}(?:-[0-9Xx])?" + _FIM_RG + ")"
    r"|(?i:\b(?:R\.G\.|RG\b|identidade\b|registro geral\b))\s*(?:n[º°o]\.?\s*)?[:\-]?\s*"
    r"(?P<valor_rotulado>(?<![\d.])\d{5,9}(?:-[0-9Xx])?" + _FIM_RG + ")"
)


# Data de nascimento pelo contexto: so a data depois de um rotulo de
# nascimento ("data de nascimento", "nascido(a) em", "DN:", "dt. nasc.",
# "nasc."). A data de vigencia, assinatura ou publicacao nao tem rotulo e
# fica de fora. O grupo `valor` e so a data: a tarja nao cobre o rotulo.
DATA_NASC_PATTERN = re.compile(
    r"(?i:\bnascid[oa]\s+(?:em|no\s+dia)|\bdata\s+de\s+nascimento|\bdt\.?\s*(?:de\s+)?nasc(?:imento)?\.?"
    r"|\bnasc\.|\bd\.?n\.?(?=\s*:))"
    r"\s*[:\-]?\s*(?:em\s+)?"
    r"(?P<valor>\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}(?!\d)"
    r"|\d{1,2}\s+de\s+(?i:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4})"
)

# CEP (#83). Formato 00000-000 ou 00.000-000, ou 8 digitos seguidos depois
# do rotulo "CEP". Sem rotulo, 8 digitos seguidos nao sao CEP (protocolo,
# matricula). As travas impedem casar trecho de telefone (99876-5432 tem 4
# digitos depois do traco), de processo e de numero maior.
CEP_PATTERN = re.compile(
    r"(?P<valor>(?<![\d.\-/])(?:\d{5}|\d{2}\.\d{3})-\d{3}(?![\d\-/])(?![.,]\d))"
    r"|(?i:\bCEP\b)\s*(?:n[º°o]\.?\s*)?[:\-]?\s*(?P<valor_rotulado>(?<![\d.])\d{8}(?!\d)(?![.,]\d))"
)

# CNH (#83). Tem 11 digitos, como o CPF; para nao confundir, so vale depois
# de um rotulo de habilitacao, e o digito verificador e conferido
# (validadores.cnh_valida). O CPF continua exigindo pontos e traco.
CNH_PATTERN = re.compile(
    r"(?i:\bCNH\b|habilita[çc][ãa]o\b)[^\d\n]{0,25}?"
    r"(?P<valor>(?<![\d.])\d{11}(?!\d)(?![.,]\d))"
)

# Cartao de pagamento (#83). Grupos 4-4-4-4 (ou 4-6-5 da Amex) com o mesmo
# separador, ou 13 a 19 digitos seguidos depois de "cartao". Sempre conferido
# pelo algoritmo de Luhn (validadores.cartao_valido): codigo de barras e
# linha digitavel no mesmo formato quase nunca passam.
CARTAO_PATTERN = re.compile(
    r"(?P<valor>(?<![\d.\-])(?:\d{4}(?P<sep>[ \-])\d{4}(?P=sep)\d{4}(?P=sep)\d{4}"
    r"|\d{4}(?P<sep_amex>[ \-])\d{6}(?P=sep_amex)\d{5})(?![\d\-]))"
    r"|(?i:\bcart[ãa]o\b)[^\d\n]{0,25}?(?P<valor_rotulado>(?<![\d.])\d{13,19}(?!\d)(?![.,]\d))"
)


def valor_detectado(match: re.Match) -> str:
    """Valor a tarjar: o grupo `valor...` que casou, ou o trecho inteiro."""
    grupos = [v for nome, v in match.groupdict().items() if nome.startswith("valor") and v]
    return grupos[0] if grupos else match.group()


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
