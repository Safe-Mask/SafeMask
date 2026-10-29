"""Upload recusa PDF corrompido e PDF protegido por senha, sem gravar nada.

A assinatura `%PDF-` deixava passar um download interrompido ou um PDF com
senha: os dois so falhavam no scanner, como erro 500 com a mensagem tecnica
da biblioteca. Agora o PDF e aberto em memoria antes de qualquer gravacao.
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#18).
"""

import pdfplumber
from sqlalchemy.orm import sessionmaker

from app.core.security import criar_token_jwt
from app.models.documentos import Documento
from tests.conftest import CONTEUDO_PDF


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _upload(client, seed, conteudo):
    return client.post(
        "/documentos/upload",
        headers=_auth(seed["usuario"]),
        files={"file": ("contrato.pdf", conteudo, "application/pdf")},
        data={"titulo": "Contrato", "nivel_seguranca": "1", "teams": f"[{seed['equipe_a'].team_id}]"},
    )


def _com_senha(monkeypatch):
    from pdfminer.pdfdocument import PDFPasswordIncorrect
    from pdfplumber.utils.exceptions import PdfminerException

    # O pdfplumber embrulha o erro do pdfminer, como faz com um PDF cifrado.
    def abrir(*args, **kwargs):
        raise PdfminerException(PDFPasswordIncorrect())

    monkeypatch.setattr(pdfplumber, "open", abrir)


def test_pdf_valido_continua_sendo_aceito(client, seed, scanner_registrado):
    scanner_registrado([])

    resp = _upload(client, seed, CONTEUDO_PDF)

    assert resp.status_code == 201, resp.text


def test_pdf_corrompido_e_recusado_sem_gravar(client, seed, scanner_registrado, tmp_path):
    scanner = scanner_registrado([])
    # Comeca como PDF, mas o resto se perdeu (download interrompido).
    truncado = CONTEUDO_PDF[:60]

    resp = _upload(client, seed, truncado)

    assert resp.status_code == 400
    assert "corrompido" in resp.json()["detail"]
    assert scanner.chamadas == 0
    assert seed["db"].query(Documento).count() == 0
    assert not any((tmp_path / "originais").iterdir())


def test_pdf_protegido_por_senha_e_recusado(client, seed, scanner_registrado, monkeypatch):
    scanner = scanner_registrado([])
    _com_senha(monkeypatch)

    resp = _upload(client, seed, CONTEUDO_PDF)

    assert resp.status_code == 400
    assert "senha" in resp.json()["detail"]
    assert scanner.chamadas == 0


def test_lote_recusa_o_corrompido_e_aceita_o_valido(client, seed, scanner_registrado, monkeypatch):
    scanner_registrado([])
    db = seed["db"]
    fabrica = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)
    monkeypatch.setattr("app.routes.documentos.fabrica_sessao_trabalho", lambda: fabrica())

    resp = client.post(
        "/documentos/upload/lote",
        headers=_auth(seed["usuario"]),
        files=[
            ("files", ("valido.pdf", CONTEUDO_PDF, "application/pdf")),
            ("files", ("truncado.pdf", CONTEUDO_PDF[:60], "application/pdf")),
        ],
        data={"team_id": str(seed["equipe_a"].team_id), "nivel_seguranca": "1"},
    )

    assert resp.status_code == 202, resp.text
    recusados = [i for i in resp.json()["itens"] if i["status"] == "RECUSADO"]
    assert len(recusados) == 1
    assert "corrompido" in recusados[0]["motivo"]
    assert resp.json()["total_aceito"] == 1
