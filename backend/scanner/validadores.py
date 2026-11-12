"""Validação de dígito verificador para CPF e CNPJ.

Funções puras: recebem uma string em qualquer formatação (com ou sem
pontos, traço e barra), extraem os dígitos e conferem os dígitos
verificadores pelo algoritmo oficial (módulo 11).

Não dependem de banco, PDF nem do resto do scanner. Isso permite testá-las
isoladamente e reutilizá-las em outros pontos do sistema.
"""

import re

_NAO_DIGITO = re.compile(r"\D")


def apenas_digitos(valor: str) -> str:
    """Remove tudo que não for dígito. '123.456.789-09' -> '12345678909'."""
    return _NAO_DIGITO.sub("", valor or "")


def sequencia_repetida(digitos: str) -> bool:
    """True para sequências como '11111111111' ou '00000000000000'.

    Esses números passam na aritmética do dígito verificador, mas não são
    documentos válidos: são rejeitados explicitamente pela Receita Federal e
    são a fonte mais comum de falso positivo em texto (placeholders, exemplos).
    """
    return len(digitos) > 0 and digitos == digitos[0] * len(digitos)


def _digito_verificador(digitos: str, pesos: list[int]) -> int:
    """Calcula um dígito verificador pelo módulo 11.

    Multiplica cada dígito pelo peso correspondente, soma tudo e tira o resto
    da divisão por 11. Resto 0 ou 1 -> dígito 0; senão -> 11 - resto.
    """
    soma = sum(int(d) * p for d, p in zip(digitos, pesos, strict=True))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(valor: str) -> bool:
    """Confere se o valor é um CPF com dígitos verificadores corretos.

    Regras:
    - exatamente 11 dígitos após remover a formatação;
    - não pode ser sequência repetida (111.111.111-11);
    - o 10º dígito é calculado a partir dos 9 primeiros com pesos 10..2;
    - o 11º dígito é calculado a partir dos 10 primeiros com pesos 11..2.
    """
    d = apenas_digitos(valor)
    if len(d) != 11 or sequencia_repetida(d):
        return False
    dv1 = _digito_verificador(d[:9], list(range(10, 1, -1)))
    dv2 = _digito_verificador(d[:10], list(range(11, 1, -1)))
    return d[9] == str(dv1) and d[10] == str(dv2)


# Pesos do CNPJ. Diferente do CPF, não são uma sequência simples: começam em
# 5 (ou 6, para o segundo dígito), descem até 2, recomeçam em 9 e descem até 2.
_PESOS_CNPJ_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS_CNPJ_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


_CNPJ_FORMATACAO = re.compile(r"[.\-/\s]")
_CNPJ_BASE_ALFANUMERICA = re.compile(r"^[0-9A-Z]{12}[0-9]{2}$")


def _dv_cnpj(base: str, pesos: list[int]) -> int:
    """DV do CNPJ pelo módulo 11, com o valor de cada caractere = ASCII - 48.

    Dígito vale ele mesmo ('0' = 48 - 48 = 0); 'A' = 65 - 48 = 17, ..., 'Z' = 42
    (IN RFB 2.229/2024). Para CNPJ só numérico, é o cálculo de sempre.
    """
    resto = sum((ord(c) - 48) * p for c, p in zip(base, pesos, strict=True)) % 11
    return 0 if resto < 2 else 11 - resto


def cnpj_valido(valor: str) -> bool:
    """Confere se o valor é um CNPJ, numérico ou alfanumérico, com DV correto.

    Regras:
    - 14 caracteres após remover a formatação (pontos, barra, traço);
    - os 12 primeiros são dígitos ou letras (CNPJ alfanumérico, IN RFB
      2.229/2024); os 2 últimos são sempre dígitos;
    - não pode ser sequência repetida (00.000.000/0000-00);
    - o 13º e o 14º são calculados pelo módulo 11 (ver `_dv_cnpj`).
    """
    d = _CNPJ_FORMATACAO.sub("", valor or "").upper()
    if not _CNPJ_BASE_ALFANUMERICA.match(d) or sequencia_repetida(d):
        return False
    dv1 = _dv_cnpj(d[:12], _PESOS_CNPJ_DV1)
    dv2 = _dv_cnpj(d[:12] + str(dv1), _PESOS_CNPJ_DV2)
    return d[12:] == f"{dv1}{dv2}"


def cnh_valida(valor: str) -> bool:
    """Confere o numero de registro da CNH (11 digitos) pelo DV do Denatran (#83).

    - 1o DV: os 9 primeiros digitos com pesos 9..1; resto da divisao por 11.
      Resto 10 vira 0 e gera um "desconto" de 2 no segundo digito.
    - 2o DV: os 9 primeiros com pesos 1..9; resto por 11 menos o desconto
      (resto 10 vira 0). Resultado negativo nao corresponde a nenhum digito.
    """
    d = apenas_digitos(valor)
    if len(d) != 11 or sequencia_repetida(d):
        return False
    soma = sum(int(x) * peso for x, peso in zip(d[:9], range(9, 0, -1), strict=True))
    dv1, desconto = soma % 11, 0
    if dv1 >= 10:
        dv1, desconto = 0, 2
    resto = sum(int(x) * peso for x, peso in zip(d[:9], range(1, 10), strict=True)) % 11
    dv2 = 0 if resto >= 10 else resto - desconto
    return d[9:] == f"{dv1}{dv2}"


def cartao_valido(valor: str) -> bool:
    """Confere um numero de cartao de pagamento pelo algoritmo de Luhn (#83).

    De 13 a 19 digitos, sem sequencia repetida. Da direita para a esquerda,
    dobra um digito sim, outro nao (subtraindo 9 quando passa de 9); a soma
    precisa terminar em 0.
    """
    d = apenas_digitos(valor)
    if not 13 <= len(d) <= 19 or sequencia_repetida(d):
        return False
    soma = 0
    for posicao, caractere in enumerate(reversed(d)):
        n = int(caractere)
        if posicao % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        soma += n
    return soma % 10 == 0


_MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
_DATA_NUMERICA = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$")
_DATA_POR_EXTENSO = re.compile(r"^(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})$", re.IGNORECASE)


def data_nascimento_valida(valor: str) -> bool:
    """Confere se o texto é uma data que existe e pode ser de nascimento.

    Aceita dd/mm/aaaa (ou com ponto ou traço) e "5 de março de 1979". O dia
    precisa existir no mês (31/02 não vale; 29/02 só em ano bissexto), e o
    ano fica entre 1900 e o ano atual: data no futuro não é nascimento.
    """
    from datetime import date

    texto = (valor or "").strip()
    numerica = _DATA_NUMERICA.match(texto)
    if numerica:
        dia, mes, ano = (int(x) for x in numerica.groups())
    else:
        extenso = _DATA_POR_EXTENSO.match(texto)
        if not extenso or extenso.group(2).lower() not in _MESES:
            return False
        dia, mes, ano = int(extenso.group(1)), _MESES[extenso.group(2).lower()], int(extenso.group(3))
    try:
        data = date(ano, mes, dia)
    except ValueError:
        return False
    return data.year >= 1900 and data <= date.today()


# Mapa usado pelo scanner: tipo de entidade -> função que valida o valor.
# Tipos ausentes daqui não passam por validação nenhuma (comportamento atual).
VALIDADORES = {
    "CPF": cpf_valido,
    "CNPJ": cnpj_valido,
    "CNH": cnh_valida,
    "CARTAO": cartao_valido,
    "DATA_NASC": data_nascimento_valida,
}
