"""O catálogo de telas acompanha o código (PI-III #9).

`documentation/telas.md` lista as telas do SafeMask. Este teste falha se uma tela HTML
nova não entrar no catálogo, ou se uma captura citada nele não existir.

Executar, de dentro de backend/:
    python -m pytest tests/test_catalogo_telas.py -v
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO = RAIZ / "documentation" / "telas.md"
TELAS = sorted((RAIZ / "frontend" / "html").rglob("*.html")) + [RAIZ / "index.html"]


def _texto():
    return CATALOGO.read_text(encoding="utf-8")


@pytest.mark.parametrize("tela", TELAS, ids=lambda t: t.relative_to(RAIZ).as_posix())
def test_toda_tela_esta_no_catalogo(tela):
    assert f"`{tela.relative_to(RAIZ).as_posix()}`" in _texto()


def test_capturas_citadas_existem():
    capturas = re.findall(r"\]\((telas/[^)]+)\)", _texto())
    assert len(capturas) == len(TELAS)
    faltando = [c for c in capturas if not (CATALOGO.parent / c).is_file()]
    assert faltando == []
