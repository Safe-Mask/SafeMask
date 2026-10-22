"""Deteccao de datas desligada por padrao.

O padrao de DATA_NASC casava qualquer data dd/mm/aaaa: vigencia, assinatura e
publicacao de documentos oficiais eram tarjadas como data de nascimento.
SAFEMASK_DETECTAR_DATAS=1 religa. Trazido do PI-III (CAMPUSCEUB/SafeMask#177).
"""

import pytest

from scanner.scanner import DocumentScanner, configuracoes_regex, detectar_datas


def test_scanner_nao_procura_datas_por_padrao(monkeypatch):
    monkeypatch.delenv("SAFEMASK_DETECTAR_DATAS", raising=False)

    assert "DATA_NASC" not in DocumentScanner().regex_config


@pytest.mark.parametrize("valor", ["1", "true", "sim", " SIM "])
def test_variavel_religa_as_datas(monkeypatch, valor):
    monkeypatch.setenv("SAFEMASK_DETECTAR_DATAS", valor)

    assert "DATA_NASC" in DocumentScanner().regex_config


@pytest.mark.parametrize("valor", ["", "0", "nao", "false"])
def test_outros_valores_mantem_as_datas_desligadas(monkeypatch, valor):
    monkeypatch.setenv("SAFEMASK_DETECTAR_DATAS", valor)

    assert detectar_datas() is False


def test_nivel_da_data_continua_na_tabela_de_niveis():
    """A paridade regex x NER e a escala de niveis nao mudam."""
    assert configuracoes_regex()["DATA_NASC"]["level"] == 2
