"""Serializacao de datas da API.

O banco grava `criado_em` em UTC e sem fuso (`TIMESTAMP` com `now()`).
Enviada sem fuso, a data era lida pelo navegador como hora local: em
Brasilia, 3 horas adiantada. Toda data que a API devolve passa por aqui e sai
com o fuso explicito; o navegador converte para a hora de quem ve.
"""

from datetime import UTC, datetime


def iso_utc(valor: datetime | None) -> str | None:
    """ISO 8601 em UTC com o fuso explicito (`...+00:00`); None continua None.

    Valor sem fuso e tratado como UTC, que e como o banco grava.
    """
    if valor is None:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=UTC)
    return valor.astimezone(UTC).isoformat()
