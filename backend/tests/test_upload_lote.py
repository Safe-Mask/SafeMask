"""Upload em lote: varios PDFs numa so requisicao, com fila de processamento.

O modo distribuicao do SafeMask (servidor da empresa) comeca na ingestao em
volume: a rota aceita o lote rapido, recusa nominalmente o arquivo invalido e
deixa o scan rodar em background (fila sincrona nos testes). Trilha no
PLANO_SERVIDOR.md, fase 1.
"""

from sqlalchemy.orm import sessionmaker

from app.core.security import criar_token_jwt
from app.models.documentos import Documento
from app.models.log_auditoria import LogAuditoria
from tests.conftest import CONTEUDO_PDF

INVALIDO = b"nao-e-um-pdf"  # nome com .pdf, mas o magic bytes rejeita


def _auth(usuario):
    return {
        "Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"
    }


def _fabrica_do_teste(db_session):
    """Fila sincrona com sessao NO banco do teste, sem reusar db_session.

    O worker de producao abre SessionLocal; aqui a sessao equivalente aponta
    para o SQLite temporario da suite. Nao pode ser a proprio db_session,
    porque a tarefa a fecharia ao terminar o processamento.
    """
    Fabrica = sessionmaker(bind=db_session.get_bind(), autoflush=False, autocommit=False)
    return Fabrica


def _lote(client, seed, arquivos, monkeypatch, team_id=None):
    db = seed["db"]
    monkeypatch.setattr(
        "app.routes.documentos.fabrica_sessao_trabalho",
        lambda: _fabrica_do_teste(db)(),
    )
    return client.post(
        "/documentos/upload/lote",
        headers=_auth(seed["usuario"]),
        files=arquivos,
        data={
            "team_id": str(team_id if team_id is not None else seed["equipe_a"].team_id),
            "nivel_seguranca": "1",
        },
    )


def test_lote_aceita_varios_e_fica_concluido(client, seed, scanner_registrado, monkeypatch):
    scanner_registrado([])
    resposta = _lote(
        client, seed,
        [
            ("files", ("contrato1.pdf", CONTEUDO_PDF, "application/pdf")),
            ("files", ("contrato2.pdf", CONTEUDO_PDF, "application/pdf")),
        ],
        monkeypatch,
    )

    assert resposta.status_code == 202, resposta.text
    corpo = resposta.json()
    assert corpo["total_recebido"] == 2
    assert corpo["total_aceito"] == 2
    assert all(item["doc_id"] for item in corpo["itens"])

    db = seed["db"]
    db.expire_all()
    docs = (
        db.query(Documento)
        .filter(Documento.doc_id.in_([i["doc_id"] for i in corpo["itens"]]))
        .all()
    )
    assert len(docs) == 2
    # A fila roda sincrona nos testes: cada doc sai AGUARDANDO e fica
    # CONCLUIDO com o PDF tarjado gravado.
    assert all(d.status_processamento == "CONCLUIDO" for d in docs)
    assert all(d.caminho_storage for d in docs)
    assert {d.nome_original for d in docs} == {"contrato1", "contrato2"}


def test_arquivo_invalido_nao_trava_o_lote(client, seed, scanner_registrado, monkeypatch):
    scanner_registrado([])
    resposta = _lote(
        client, seed,
        [
            ("files", ("valido.pdf", CONTEUDO_PDF, "application/pdf")),
            ("files", ("quebrado.pdf", INVALIDO, "application/pdf")),
        ],
        monkeypatch,
    )

    assert resposta.status_code == 202, resposta.text
    corpo = resposta.json()
    assert corpo["total_aceito"] == 1
    recusados = [i for i in corpo["itens"] if i["status"] == "RECUSADO"]
    aceitos = [i for i in corpo["itens"] if i["status"] == "AGUARDANDO"]
    assert len(recusados) == 1
    assert len(aceitos) == 1
    assert "PDF" in recusados[0]["motivo"]
    assert recusados[0]["doc_id"] is None

    db = seed["db"]
    db.expire_all()
    aceito = db.get(Documento, aceitos[0]["doc_id"])
    assert aceito.status_processamento == "CONCLUIDO"


def test_lote_somente_invalidos_nao_cria_documento(client, seed, monkeypatch):
    resposta = _lote(
        client, seed,
        [
            ("files", ("lixo1.pdf", INVALIDO, "application/pdf")),
            ("files", ("lixo2.pdf", INVALIDO, "application/pdf")),
        ],
        monkeypatch,
    )

    assert resposta.status_code == 202, resposta.text
    corpo = resposta.json()
    assert corpo["total_aceito"] == 0
    assert all(i["status"] == "RECUSADO" for i in corpo["itens"])

    db = seed["db"]
    db.expire_all()
    assert (
        db.query(Documento).filter(Documento.user_team_id == seed["user_team_a"]).count() == 0
    )


def test_lote_fora_da_equipe_vira_403(client, seed, monkeypatch):
    resposta = _lote(
        client, seed,
        [("files", ("contrato.pdf", CONTEUDO_PDF, "application/pdf"))],
        monkeypatch,
        team_id=seed["equipe_globex"].team_id,  # equipe de outra organizacao
    )
    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Voce nao faz parte dessa equipe."


def test_lote_acima_do_limite_vira_400(client, seed, monkeypatch):
    from app.routes.documentos import MAX_ARQUIVOS_POR_LOTE

    resposta = _lote(
        client, seed,
        [
            ("files", (f"arquivo_{n}.pdf", CONTEUDO_PDF, "application/pdf"))
            for n in range(MAX_ARQUIVOS_POR_LOTE + 1)
        ],
        monkeypatch,
    )
    assert resposta.status_code == 400
    assert "Limite" in resposta.json()["detail"]


def test_lote_registra_auditoria_com_detalhe(client, seed, scanner_registrado, monkeypatch):
    scanner_registrado([])
    resposta = _lote(
        client, seed,
        [
            ("files", ("contrato1.pdf", CONTEUDO_PDF, "application/pdf")),
            ("files", ("quebrado.pdf", INVALIDO, "application/pdf")),
        ],
        monkeypatch,
    )

    assert resposta.status_code == 202
    corpo = resposta.json()
    db = seed["db"]
    db.expire_all()
    eventos = (
        db.query(LogAuditoria)
        .filter_by(acao="upload_documento", user_id=seed["usuario"].user_id)
        .all()
    )
    aceitos = [i for i in corpo["itens"] if i["status"] == "AGUARDANDO"]
    assert {e.doc_id for e in eventos} == {i["doc_id"] for i in aceitos}
    assert all(e.detalhe == "lote_aguardando" for e in eventos)


def test_falha_no_scan_marca_o_doc_como_erro(client, seed, scanner_registrado, monkeypatch):
    """Arquivo aceito, scan estourando: doc termina ERRO e fica visivel."""
    scanner = scanner_registrado([])

    def scan_quebrado(*args, **kwargs):
        raise RuntimeError("falha de OCR")

    original = scanner.scan_and_save
    scanner.scan_and_save = scan_quebrado

    resposta = _lote(
        client, seed,
        [("files", ("contrato.pdf", CONTEUDO_PDF, "application/pdf"))],
        monkeypatch,
    )

    assert resposta.status_code == 202
    doc_id = resposta.json()["itens"][0]["doc_id"]
    db = seed["db"]
    db.expire_all()
    assert db.get(Documento, doc_id).status_processamento == "ERRO"
    scanner.scan_and_save = original
