"""XSS via conteudo de arquivo enviado pelo usuario.

Um PDF pode embutir JavaScript e acoes. Servir o arquivo `inline` sob a mesma
origem da aplicacao permitiria que esse script rodasse com as credenciais de
quem abriu o preview. Estes testes travam esse caminho.
"""

CONTEUDO_PDF_COM_JS = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Action /S /JavaScript /JS (app.alert('xss')) >>\nendobj\n"
    b"trailer\n<< /OpenAction 1 0 R >>\n%%EOF\n"
)


def _criar_documento(seed, caminho_conteudo, nome="ata.pdf"):
    """Documento censurado apontando para um arquivo real em disco.

    Grava tambem o "original" com o mesmo hash, porque `/original` e `/parcial`
    procuram por `{hash_documento}*` em ORIGINAIS_DIR.
    """
    from app.models.documentos import Documento
    from app.routes import documentos as documentos_routes

    caminho_conteudo.write_bytes(CONTEUDO_PDF_COM_JS)
    documentos_routes.ORIGINAIS_DIR.mkdir(parents=True, exist_ok=True)
    (documentos_routes.ORIGINAIS_DIR / f"{caminho_conteudo.stem}.pdf").write_bytes(
        CONTEUDO_PDF_COM_JS
    )

    documento = Documento(
        user_team_id=seed["user_team_a"],
        nome_original=nome,
        extensao=".pdf",
        tamanho_bytes=len(CONTEUDO_PDF_COM_JS),
        nivel_seguranca=1,
        chave_criptografica="chave-teste",
        hash_documento=caminho_conteudo.stem,
        caminho_storage=str(caminho_conteudo),
        status_processamento="CONCLUIDO",
        ativo=True,
    )
    seed["db"].add(documento)
    seed["db"].commit()
    seed["db"].refresh(documento)
    return documento


def _token(usuario):
    from app.core.security import criar_token_jwt

    token = criar_token_jwt({"sub": usuario.email, "nome": usuario.nome})
    return {"Authorization": f"Bearer {token}"}


def _baixar(client, seed, doc_id, rota):
    resp = client.get(f"/documentos{rota.format(doc_id=doc_id)}", headers=_token(seed["usuario"]))
    assert resp.status_code == 200, resp.text
    return resp


def test_preview_nao_serve_html(client, seed, tmp_path):
    """O `media_type` e forcado: um `.pdf` nunca vira `text/html`."""
    documento = _criar_documento(seed, tmp_path / "doc.pdf")

    resp = _baixar(client, seed, documento.doc_id, "/censurados/{doc_id}/arquivo")

    assert resp.headers["content-type"] == "application/pdf"
    assert "text/html" not in resp.headers["content-type"]


def test_preview_tem_nosniff(client, seed, tmp_path):
    """`nosniff` impede que o navegador reinterprete o tipo e execute script."""
    documento = _criar_documento(seed, tmp_path / "doc.pdf")

    resp = _baixar(client, seed, documento.doc_id, "/censurados/{doc_id}/arquivo")

    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_preview_bloqueia_script_com_csp(client, seed, tmp_path):
    """CSP com `script-src 'none'` e `sandbox` trava o JS embutido no PDF."""
    documento = _criar_documento(seed, tmp_path / "doc.pdf")

    resp = _baixar(client, seed, documento.doc_id, "/censurados/{doc_id}/arquivo")

    csp = resp.headers.get("Content-Security-Policy", "")
    assert "script-src 'none'" in csp
    assert "sandbox" in csp
    assert "object-src 'none'" in csp


def test_preview_preserva_o_conteudo_para_exibicao(client, seed, tmp_path):
    """A trava e de execucao, nao de integridade: o PDF chega intacto."""
    documento = _criar_documento(seed, tmp_path / "doc.pdf")

    resp = _baixar(client, seed, documento.doc_id, "/censurados/{doc_id}/arquivo")

    assert resp.content == CONTEUDO_PDF_COM_JS


def test_original_e_parcial_tambem_travam_script(client, seed, tmp_path):
    """Original e parcial tambem sao conteudo do usuario."""
    from app.core import file_responses

    documento = _criar_documento(seed, tmp_path / "doc.pdf")
    headers = _token(seed["usuario"])

    original = client.get(f"/documentos/{documento.doc_id}/original", headers=headers)
    parcial = client.get(f"/documentos/{documento.doc_id}/parcial", headers=headers)

    for resp in (original, parcial):
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert "script-src 'none'" in resp.headers.get("Content-Security-Policy", "")
        assert resp.headers["content-type"] == "application/pdf"
    assert file_responses.CSP_ARQUIVO


def test_respostas_de_arquivo_baixam_por_padrao(client, seed, tmp_path):
    """So o preview e inline; original e parcial sao download."""
    documento = _criar_documento(seed, tmp_path / "doc.pdf")
    headers = _token(seed["usuario"])

    preview = _baixar(client, seed, documento.doc_id, "/censurados/{doc_id}/arquivo")
    original = client.get(f"/documentos/{documento.doc_id}/original", headers=headers)

    assert preview.headers["content-disposition"].startswith("inline")
    assert original.headers["content-disposition"].startswith("attachment")


def test_nome_do_arquivo_nao_injeta_header(client, seed, tmp_path):
    """`filename` vem do cliente; um nome com aspas não pode quebrar o header."""
    documento = _criar_documento(
        seed, tmp_path / "doc.pdf", nome='ata"; injected="1'
    )

    resp = _baixar(client, seed, documento.doc_id, "/censurados/{doc_id}/arquivo")

    disposition = resp.headers["content-disposition"]
    # O FileResponse escapa o nome; o importante e que o header continua unico.
    assert disposition.count("filename") == 1
    assert "\n" not in disposition
    assert "\r" not in disposition
