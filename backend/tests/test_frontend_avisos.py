"""Nenhuma tela usa as caixas do navegador (PBI E6-04, #195, Task #216).

As 19 chamadas de `alert()` e `confirm()` foram trocadas pelos avisos e
pela janela de confirmação do site (`frontend/js/avisos.js`). Este teste
recusa qualquer `alert`, `confirm` ou `prompt` novo no frontend e confere
que toda tela que usa `avisar()` ou `confirmar()` carrega o componente
antes do próprio script, junto com a folha `css/avisos.css`.

Executar, de dentro de backend/:
    python -m pytest tests/test_frontend_avisos.py -v
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
FRONTEND_JS = RAIZ / "frontend" / "js"
TELAS = sorted((RAIZ / "frontend" / "html").rglob("*.html"))

CAIXA_DO_NAVEGADOR = re.compile(r"(?<![\w.$])(?:window\.)?(alert|confirm|prompt)\s*\(")
USA_AVISOS = re.compile(r"(?<![\w.])(avisar|avisarDepois|confirmar)\s*\(")
SCRIPT = re.compile(r'<script[^>]+src="([^"]+)"', re.IGNORECASE)
FOLHA = re.compile(r'<link[^>]+href="([^"]+\.css)[^"]*"', re.IGNORECASE)


def _sem_comentarios(js: str) -> str:
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$", "", js)


def test_nenhuma_caixa_do_navegador_no_frontend():
    achados = [
        f"{arquivo.relative_to(FRONTEND_JS)}: {m.group(0)}"
        for arquivo in sorted(FRONTEND_JS.rglob("*.js"))
        for m in CAIXA_DO_NAVEGADOR.finditer(_sem_comentarios(arquivo.read_text(encoding="utf-8")))
    ]
    assert achados == []


def test_componente_existe():
    js = (FRONTEND_JS / "avisos.js").read_text(encoding="utf-8")
    assert "window.avisar" in js and "window.confirmar" in js
    assert (RAIZ / "frontend" / "css" / "avisos.css").is_file()


@pytest.mark.parametrize("tela", TELAS, ids=lambda t: t.relative_to(RAIZ).as_posix())
def test_tela_que_usa_avisos_carrega_o_componente(tela):
    html = tela.read_text(encoding="utf-8")
    scripts = [(tela.parent / s.split("?")[0]).resolve() for s in SCRIPT.findall(html) if not s.startswith("http")]
    usam = [s for s in scripts if s.is_file() and USA_AVISOS.search(_sem_comentarios(s.read_text(encoding="utf-8")))]
    usam = [s for s in usam if s.name != "avisos.js"]
    if not usam:
        pytest.skip("a tela não usa avisos")

    componente = (FRONTEND_JS / "avisos.js").resolve()
    assert componente in scripts, "a tela usa avisar/confirmar mas não carrega js/avisos.js"
    assert scripts.index(componente) < min(scripts.index(s) for s in usam), "avisos.js precisa vir antes do script da tela"
    folhas = [(tela.parent / f).resolve().name for f in FOLHA.findall(html)]
    assert "avisos.css" in folhas
