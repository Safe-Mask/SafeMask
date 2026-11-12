"""Configuração do teste de interface (PI-III #16).

Fica fora de `testpaths` (pytest.ini) e roda só quando pedido, porque abre um
navegador e sobe a API:

    cd backend
    SAFEMASK_TESTE_INTERFACE=1 python -m pytest tests_interface -v

No Windows (PowerShell): `$env:SAFEMASK_TESTE_INTERFACE=1`. O navegador é
o Chromium do Playwright (`python -m playwright install chromium`); para
usar o Edge já instalado, `SAFEMASK_UI_NAVEGADOR=msedge`.
"""

import os

import pytest

ATIVO = os.getenv("SAFEMASK_TESTE_INTERFACE") == "1"


def pytest_collection_modifyitems(config, items):
    if ATIVO:
        return
    pular = pytest.mark.skip(reason="teste de interface: defina SAFEMASK_TESTE_INTERFACE=1")
    for item in items:
        if "tests_interface" in str(item.fspath):
            item.add_marker(pular)


@pytest.fixture(scope="session")
def ambiente(tmp_path_factory):
    from tests_interface.servidores import Ambiente

    amb = Ambiente(tmp_path_factory.mktemp("ui")).iniciar()
    yield amb
    amb.encerrar()


@pytest.fixture(scope="session")
def navegador():
    from playwright.sync_api import sync_playwright

    canal = os.getenv("SAFEMASK_UI_NAVEGADOR") or None
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=canal, headless=True)
        yield browser
        browser.close()


@pytest.fixture
def pagina(navegador):
    contexto = navegador.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True)
    page = contexto.new_page()
    page.set_default_timeout(20000)
    erros = []
    page.on("pageerror", lambda e: erros.append(str(e)))
    yield page
    contexto.close()
    assert erros == [], f"erros de JavaScript na tela: {erros}"
