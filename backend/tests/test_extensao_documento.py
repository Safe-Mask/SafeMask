"""Extensao do documento e nome do download.

O scanner real tira a extensao do `nome_original`, que no upload e o titulo
digitado ("Contrato", sem extensao): o documento principal ficava com
`extensao` vazia, e o download do censurado, montado como
`{nome}{extensao}`, saia sem ".pdf" (ou "Contratopdf" nas copias).
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#168).
"""

import pytest
from sqlalchemy import create_engine, text

from app.core.security import criar_token_jwt
from app.models.documentos import Documento
from tests.conftest import CONTEUDO_PDF

AUTH = {"Authorization": f"Bearer {criar_token_jwt({'sub': 'ana@safemask.example.com', 'nome': 'Ana'})}"}


def _scanner_como_o_real(scanner_registrado):
    """ScannerFalso que, como o real, deixa a extensao vazia no principal."""
    scanner = scanner_registrado([(3, 1)])
    original = scanner.scan_and_save

    def scan_and_save(*args, **kwargs):
        resultado = original(*args, **kwargs)
        db = kwargs.get("db") or args[1]
        db.get(Documento, resultado["doc_id"]).extensao = ""
        db.flush()
        return resultado

    scanner.scan_and_save = scan_and_save
    return scanner


def _upload(client, seed):
    resp = client.post(
        "/documentos/upload",
        headers=AUTH,
        files={"file": ("contrato.pdf", CONTEUDO_PDF, "application/pdf")},
        data={
            "titulo": "Contrato",
            "nivel_seguranca": "1",
            "teams": f"[{seed['equipe_a'].team_id}, {seed['equipe_b'].team_id}]",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_principal_e_copias_gravam_a_extensao_do_arquivo(client, seed, scanner_registrado):
    _scanner_como_o_real(scanner_registrado)

    resposta = _upload(client, seed)

    docs = seed["db"].query(Documento).filter_by(hash_documento=resposta["hash"]).all()
    assert len(docs) == 2
    assert {d.extensao for d in docs} == {"pdf"}


def test_download_do_censurado_sai_com_ponto_pdf(client, seed, scanner_registrado):
    _scanner_como_o_real(scanner_registrado)
    resposta = _upload(client, seed)

    for doc in seed["db"].query(Documento).filter_by(hash_documento=resposta["hash"]).all():
        resp = client.get(f"/documentos/censurados/{doc.doc_id}/arquivo", headers=AUTH)
        assert resp.status_code == 200, resp.text
        assert "Contrato.pdf" in resp.headers["content-disposition"]


@pytest.mark.parametrize("nome, extensao, esperado", [
    ("Contrato", "pdf", "Contrato.pdf"),
    ("Contrato", ".pdf", "Contrato.pdf"),
    ("contrato.pdf", "pdf", "contrato.pdf"),
    ("Contrato", "", "Contrato"),
    ("Contrato", None, "Contrato"),
])
def test_nome_para_download(nome, extensao, esperado):
    from app.routes.documentos import nome_para_download

    assert nome_para_download(nome, extensao) == esperado


def test_banco_existente_tem_a_extensao_corrigida(tmp_path):
    from app.database import corrigir_extensao_documentos

    engine = create_engine(f"sqlite:///{(tmp_path / 'antigo.db').as_posix()}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE documentos (doc_id INTEGER PRIMARY KEY, extensao VARCHAR(20))"))
        conn.execute(text("INSERT INTO documentos (extensao) VALUES (''), ('.pdf'), ('pdf'), ('.PDF')"))

    corrigir_extensao_documentos(engine)
    corrigir_extensao_documentos(engine)  # segunda execucao nao muda nada

    with engine.connect() as conn:
        valores = [r[0] for r in conn.execute(text("SELECT extensao FROM documentos ORDER BY doc_id"))]
    assert valores == ["pdf", "pdf", "pdf", "pdf"]
