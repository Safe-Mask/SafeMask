"""O atributo `hidden` esconde de fato em todas as telas (bug #193).

Na tela Documentos Censurados, `.detail-empty` e `.detail-shell` declaram
`display: grid`, e uma regra de classe vence o `display: none` que o
navegador aplica ao atributo `hidden`. Resultado: "Fechar detalhes" não
fechava e "Selecione um documento" aparecia junto com os detalhes.

A correção é global: toda tela carrega uma folha base com
`[hidden] { display: none !important; }`. Este teste lê os HTML e as
folhas de estilo locais que cada um carrega e recusa a tela sem essa regra.

Executar, de dentro de backend/:
    python -m pytest tests/test_frontend_hidden.py -v
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
TELAS = sorted((RAIZ / "frontend" / "html").rglob("*.html")) + [RAIZ / "index.html"]

LINK_CSS = re.compile(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', re.IGNORECASE)
# Regra no nível de topo, com o seletor exatamente `[hidden]`.
REGRA_HIDDEN = re.compile(
    r"^\s*\[hidden\]\s*\{[^}]*display\s*:\s*none\s*!important",
    re.IGNORECASE | re.MULTILINE,
)


def _folhas_locais(tela: Path) -> list[Path]:
    html = tela.read_text(encoding="utf-8")
    folhas = []
    for href in LINK_CSS.findall(html):
        if href.startswith("http"):
            continue
        folhas.append((tela.parent / href.split("?")[0]).resolve())
    return folhas


def test_telas_encontradas():
    assert len(TELAS) >= 12


@pytest.mark.parametrize("tela", TELAS, ids=lambda t: t.relative_to(RAIZ).as_posix())
def test_tela_carrega_regra_global_do_hidden(tela):
    folhas = _folhas_locais(tela)
    assert folhas, "a tela não carrega nenhuma folha de estilo local"
    com_regra = [f for f in folhas if REGRA_HIDDEN.search(f.read_text(encoding="utf-8"))]
    assert com_regra, (
        "nenhuma folha carregada tem `[hidden] { display: none !important; }`: "
        "uma classe com `display` venceria o atributo hidden (#193)"
    )
