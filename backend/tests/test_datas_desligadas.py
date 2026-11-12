"""Datas de documento nao sao tarjadas.

O padrao antigo de DATA_NASC casava qualquer data dd/mm/aaaa: vigencia,
assinatura e publicacao de documentos oficiais eram tarjadas como data de
nascimento (PI-III #177). Desde a deteccao pelo contexto (PI-III #178), a data
so conta depois de um rotulo de nascimento; SAFEMASK_DETECTAR_DATAS=1 religa
o modo antigo.
"""

import pytest

from scanner.scanner import DocumentScanner, configuracoes_regex, detectar_datas


def test_por_padrao_a_data_depende_do_rotulo(monkeypatch):
    from scanner.patterns import DATA_NASC_PATTERN

    monkeypatch.delenv("SAFEMASK_DETECTAR_DATAS", raising=False)

    assert DocumentScanner().regex_config["DATA_NASC"]["pattern"] == DATA_NASC_PATTERN.pattern


@pytest.mark.parametrize("valor", ["1", "true", "sim", " SIM "])
def test_variavel_religa_o_modo_antigo(monkeypatch, valor):
    from scanner.scanner import DATA_ANTIGA_PATTERN

    monkeypatch.setenv("SAFEMASK_DETECTAR_DATAS", valor)

    assert DocumentScanner().regex_config["DATA_NASC"]["pattern"] == DATA_ANTIGA_PATTERN


@pytest.mark.parametrize("valor", ["", "0", "nao", "false"])
def test_outros_valores_mantem_as_datas_desligadas(monkeypatch, valor):
    monkeypatch.setenv("SAFEMASK_DETECTAR_DATAS", valor)

    assert detectar_datas() is False


def test_nivel_da_data_continua_na_tabela_de_niveis():
    """A paridade regex x NER e a escala de niveis nao mudam."""
    assert configuracoes_regex()["DATA_NASC"]["level"] == 2
