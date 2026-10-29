"""Nenhuma tela escreve senha ou token no console do navegador.

A tela de cadastro fazia console.log de { nome, email, senha } antes do
envio. Este teste le os scripts do frontend e recusa qualquer chamada
console.* que mencione senha, password ou token.
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#189).
"""

import re
from pathlib import Path

FRONTEND_JS = Path(__file__).resolve().parents[2] / "frontend" / "js"
CONSOLE_COM_SEGREDO = re.compile(r"console\.\w+\([^;]*\b(senha|password|token)\b", re.IGNORECASE)


def test_scripts_do_frontend_existem():
    assert any(FRONTEND_JS.rglob("*.js"))


def test_nenhum_console_com_senha_ou_token():
    achados = [
        f"{arquivo.relative_to(FRONTEND_JS)}:{numero}: {linha.strip()}"
        for arquivo in sorted(FRONTEND_JS.rglob("*.js"))
        for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1)
        if CONSOLE_COM_SEGREDO.search(linha)
    ]
    assert achados == []
