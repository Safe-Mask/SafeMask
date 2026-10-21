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


def cnpj_valido(valor: str) -> bool:
    """Confere se o valor é um CNPJ com dígitos verificadores corretos.

    Regras:
    - exatamente 14 dígitos após remover a formatação;
    - não pode ser sequência repetida (00.000.000/0000-00);
    - o 13º dígito é calculado a partir dos 12 primeiros;
    - o 14º dígito é calculado a partir dos 13 primeiros.
    """
    d = apenas_digitos(valor)
    if len(d) != 14 or sequencia_repetida(d):
        return False
    dv1 = _digito_verificador(d[:12], _PESOS_CNPJ_DV1)
    dv2 = _digito_verificador(d[:13], _PESOS_CNPJ_DV2)
    return d[12] == str(dv1) and d[13] == str(dv2)


# Mapa usado pelo scanner: tipo de entidade -> função que valida o valor.
# Tipos ausentes daqui não passam por validação nenhuma (comportamento atual).
VALIDADORES = {
    "CPF": cpf_valido,
    "CNPJ": cnpj_valido,
}
