"""Fluxo principal no navegador (PI-III #16).

Login, Novo Upload com a revisão das tarjas, Documentos Censurados
(detalhes e "Fechar detalhes") e página da equipe, numa API e num banco
descartáveis. Pegaria os bugs do PI-III #187 (Equipe "-" nos detalhes), #193
("Fechar detalhes" não fechava) e #194 (cartão cortado com nome longo), e o
formulário de membros que aparecia para quem não é líder.

Executar: ver tests_interface/conftest.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import gerar_pdf_texto  # noqa: E402
from tests_interface.servidores import CONTAS, EQUIPE, SENHA  # noqa: E402

NOME_LONGO = "2020_09_23_09_08_06_5dou_publicacao3oaditivo_censurado"


def _entrar(page, ambiente, cargo):
    page.goto(f"{ambiente.telas_url}/frontend/html/auth/login.html")
    page.fill("input[type=email]", CONTAS[cargo][1])
    page.fill("input[type=password]", SENHA)
    page.press("input[type=password]", "Enter")
    page.wait_for_url("**/dashboard.html")


def _enviar_documento(page, ambiente, titulo, desmarcar=None):
    pdf = gerar_pdf_texto(["Contrato de teste", "CPF 529.982.247-25", "E-mail titular@exemplo.com.br",
                           "CNPJ 11.222.333/0001-81"])
    page.goto(f"{ambiente.telas_url}/frontend/html/documentos/censurar.html")
    page.set_input_files("#documentInput", {"name": "contrato.pdf", "mimeType": "application/pdf", "buffer": pdf})
    page.click("#censorStartBtn")
    page.wait_for_selector(".finding-item")
    assert page.locator(".finding-item").count() == 3
    # O valor aparece mascarado na revisão (#208).
    assert "529.982" not in page.inner_text("#findingsList")
    if desmarcar:
        page.locator(".finding-item", has_text=desmarcar).locator("input").uncheck()
        assert page.inner_text("#findingsCount") == "2 de 3 marcados"
    page.locator("#teamPicker label", has_text=EQUIPE).click()
    page.fill("#docTitleInput", titulo)
    page.click("#saveCensoredDocBtn")
    page.wait_for_url("**/censurados.html?doc_id=*")
    return int(page.url.split("doc_id=")[1])


def test_fluxo_do_lider(pagina, ambiente):
    page = pagina
    _entrar(page, ambiente, "lider")
    _enviar_documento(page, ambiente, NOME_LONGO, desmarcar="CNPJ")

    # Detalhes abertos, com a equipe preenchida (#187).
    page.wait_for_selector("#detailShell", state="visible")
    assert page.inner_text("#detailTeam") == EQUIPE
    assert page.is_hidden("#detailEmptyState")

    # Cartão com nome longo não sai do painel (#194).
    painel = page.locator(".docs-list-panel").bounding_box()
    cartao = page.locator(".doc-card").first.bounding_box()
    assert cartao["x"] + cartao["width"] <= painel["x"] + painel["width"] + 1

    # "Fechar detalhes" esconde os detalhes e mostra o vazio (#193).
    page.click("#closeDetailsBtn")
    assert page.is_hidden("#detailShell")
    assert page.is_visible("#detailEmptyState")

    # Página da equipe: o líder vê o formulário de membros e o documento.
    page.goto(f"{ambiente.telas_url}/frontend/html/equipes/detalhe.html?team_id={ambiente.team_id}")
    page.wait_for_selector("#memberAddForm", state="visible")
    assert NOME_LONGO in page.content()


def test_membro_nao_ve_o_formulario_de_membros(pagina, ambiente):
    page = pagina
    _entrar(page, ambiente, "membro")
    page.goto(f"{ambiente.telas_url}/frontend/html/equipes/detalhe.html?team_id={ambiente.team_id}")
    page.wait_for_load_state("networkidle")
    assert page.is_hidden("#memberAddForm")


def test_confirmacao_de_exclusao_e_do_site(pagina, ambiente):
    """A exclusão pede confirmação na janela do site (#195); cancelar não apaga."""
    page = pagina
    _entrar(page, ambiente, "lider")
    doc_id = _enviar_documento(page, ambiente, "Para cancelar a exclusao")
    page.wait_for_selector("#deleteDocBtn", state="visible")
    page.on("dialog", lambda d: (_ for _ in ()).throw(AssertionError("caixa do navegador apareceu")))
    page.click("#deleteDocBtn")
    page.wait_for_selector(".sm-confirmacao__janela")
    page.keyboard.press("Escape")
    assert page.locator(".sm-confirmacao").count() == 0
    page.reload()
    page.wait_for_selector(f".doc-card[data-doc-id='{doc_id}']")
