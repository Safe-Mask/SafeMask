"""Deteccao de RG e telefone no texto.

O RG aceitava qualquer sequencia de 7 a 9 digitos (pegava trecho de processo,
protocolo, CEP) e o telefone casava numeros longos sem separador. Telefone e
RG no fim da frase (seguidos de ponto) tambem precisam ser detectados.
Trazido do PI-III (CAMPUSCEUB/SafeMask#82 e #174), com os formatos daqui
(orgao emissor depois do RG, +55, hifen depois do DDD).
"""

import re

import pytest

from scanner.patterns import (
    PHONE_DETECTION_PATTERN,
    PHONE_PATTERN,
    RG_PATTERN,
    mask_phone,
    valor_detectado,
)
from tests.casos_rg_telefone import RG, TELEFONE


def _valores(padrao, texto):
    return [valor_detectado(m) for m in re.finditer(padrao, texto)]


@pytest.mark.parametrize("texto, esperado", RG)
def test_rg(texto, esperado):
    valores = _valores(RG_PATTERN, texto)
    assert valores == ([esperado] if esperado else []), f"RG em {texto!r}: {valores}"


@pytest.mark.parametrize("texto, esperado", TELEFONE)
def test_telefone(texto, esperado):
    valores = _valores(PHONE_DETECTION_PATTERN, texto)
    assert valores == ([esperado] if esperado else []), f"telefone em {texto!r}: {valores}"


@pytest.mark.parametrize("texto, esperado", [(t, e) for t, e in TELEFONE if e])
def test_telefone_detectado_continua_recebendo_a_mascara(texto, esperado):
    """A mascara estruturada exige PHONE_PATTERN.fullmatch no valor detectado."""
    assert PHONE_PATTERN.fullmatch(esperado)
    assert mask_phone(esperado) is not None


def test_tarja_do_rg_com_rotulo_cobre_so_o_numero():
    assert _valores(RG_PATTERN, "Identidade nº 12345678") == ["12345678"]
