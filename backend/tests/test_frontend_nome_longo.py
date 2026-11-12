"""Nome longo, sem espaço, não corta os cartões de documento (bug #194).

Com o nome `2020_09_23_09_08_06_5dou_publicacao3oaditivo_censurado`, o
cartão da lista em Documentos Censurados ficava mais largo que o painel:
item de grid e de flex tem `min-width: auto`, então cresce até caber a
palavra inteira. O painel cortava o excesso, e o botão "Detalhes" e o
fim do nome sumiam. O título nos detalhes também saía do quadro.

A correção está em `censurados.css` (usada também pela Descensura):
`min-width: 0` nos itens, `overflow-wrap: anywhere` nos nomes e
`flex-wrap: wrap` nas ações e etiquetas. A conferência visual, em 1366,
1920 e 375 px, está no PR; este teste impede que as regras se percam.

Executar, de dentro de backend/:
    python -m pytest tests/test_frontend_nome_longo.py -v
"""

import re
from pathlib import Path

import pytest

CSS = Path(__file__).resolve().parents[2] / "frontend" / "css" / "documentos" / "censurados.css"


def _declaracoes(seletor: str) -> dict[str, str]:
    """Junta as declarações de todos os blocos cujo seletor inclui `seletor`."""
    texto = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.DOTALL)
    resultado: dict[str, str] = {}
    for seletores, corpo in re.findall(r"([^{}]+)\{([^{}]*)\}", texto):
        if seletor in [s.strip() for s in seletores.split(",")]:
            for prop, valor in re.findall(r"([\w-]+)\s*:\s*([^;]+);?", corpo):
                resultado[prop.strip()] = valor.strip()
    return resultado


@pytest.mark.parametrize("seletor", [".doc-card", ".doc-card-top > div", ".detail-meta > div"])
def test_itens_podem_encolher(seletor):
    assert _declaracoes(seletor).get("min-width") == "0"


@pytest.mark.parametrize("seletor", [".doc-card strong", ".detail-meta strong"])
def test_nome_quebra_em_qualquer_ponto(seletor):
    assert _declaracoes(seletor).get("overflow-wrap") == "anywhere"


@pytest.mark.parametrize("seletor", [".doc-actions", ".doc-card-top", ".doc-card-meta"])
def test_acoes_e_etiquetas_descem_de_linha(seletor):
    assert _declaracoes(seletor).get("flex-wrap") == "wrap"


def test_lista_tem_coluna_que_encolhe():
    assert _declaracoes(".docs-list").get("grid-template-columns") == "minmax(0, 1fr)"
