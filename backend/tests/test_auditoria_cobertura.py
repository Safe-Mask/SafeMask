"""Cobertura de auditoria nos fluxos de documento e negativas (Fase 3.3)."""

from app.core.security import criar_token_jwt
from app.models.documentos import Documento
from app.models.log_auditoria import LogAuditoria
from tests.conftest import CONTEUDO_PDF


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _eventos(db, **filtros):
    db.expire_all()
    return db.query(LogAuditoria).filter_by(**filtros).order_by(LogAuditoria.log_id).all()


def _documento_sem_arquivo(seed, user_team_id, hash_documento):
    documento = Documento(
        user_team_id=user_team_id,
        nome_original="sumido.pdf",
        extensao="pdf",
        tamanho_bytes=10,
        nivel_seguranca=1,
        chave_criptografica="k",
        hash_documento=hash_documento,
        caminho_storage="/tmp/arquivo-que-nao-existe-safemask.pdf",
        status_processamento="CONCLUIDO",
        ativo=True,
    )
    seed["db"].add(documento)
    seed["db"].commit()
    seed["db"].refresh(documento)
    return documento


def test_upload_individual_negado_gera_evento(client, seed):
    resposta = client.post(
        "/documentos/upload",
        data={
            "titulo": "Contrato",
            "nivel_seguranca": "1",
            "teams": f"[{seed['equipe_a'].team_id}]",
        },
        files={"file": ("contrato.pdf", CONTEUDO_PDF, "application/pdf")},
        headers=_auth(seed["usuario_globex"]),
    )
    assert resposta.status_code == 403

    negados = _eventos(
        seed["db"], acao="upload_documento", resultado="negado",
        team_id=seed["equipe_a"].team_id,
    )
    assert len(negados) == 1
    assert negados[0].user_id == seed["usuario_globex"].user_id


def test_upload_lote_negado_gera_evento(client, seed):
    resposta = client.post(
        "/documentos/upload/lote",
        data={
            "team_id": str(seed["equipe_a"].team_id),
            "nivel_seguranca": "1",
        },
        files=[("files", ("contrato.pdf", CONTEUDO_PDF, "application/pdf"))],
        headers=_auth(seed["usuario_globex"]),
    )
    assert resposta.status_code == 403

    negados = _eventos(
        seed["db"], acao="upload_documento_lote", resultado="negado",
        team_id=seed["equipe_a"].team_id,
    )
    assert len(negados) == 1


def test_listagem_de_equipe_negada_gera_evento(client, seed):
    resposta = client.get(
        f"/documentos/listar/{seed['equipe_a'].team_id}",
        headers=_auth(seed["usuario_globex"]),
    )
    assert resposta.status_code == 403

    negados = _eventos(
        seed["db"], acao="listar_documentos", resultado="negado",
        team_id=seed["equipe_a"].team_id,
    )
    assert len(negados) == 1


def test_listagem_de_censurados_gera_evento_de_sucesso(client, seed):
    resposta = client.get(
        "/documentos/censurados",
        headers=_auth(seed["usuario"]),
    )
    assert resposta.status_code == 200

    eventos = _eventos(
        seed["db"], acao="listar_documentos", resultado="sucesso",
        detalhe="censurados",
    )
    assert len(eventos) == 1


def test_download_censurado_sem_arquivo_gera_evento_de_falha(client, seed):
    documento = _documento_sem_arquivo(seed, seed["user_team_a"], "hash-sumido-censurado")

    resposta = client.get(
        f"/documentos/censurados/{documento.doc_id}/arquivo",
        headers=_auth(seed["usuario"]),
    )
    assert resposta.status_code == 404

    falhas = _eventos(
        seed["db"], acao="ver_censurado", resultado="falha",
        doc_id=documento.doc_id, detalhe="arquivo_ausente",
    )
    assert len(falhas) == 1


def test_original_sem_arquivo_gera_evento_de_falha(client, seed):
    documento = _documento_sem_arquivo(seed, seed["user_team_a"], "hash-sumido-original")

    resposta = client.get(
        f"/documentos/{documento.doc_id}/original",
        headers=_auth(seed["usuario"]),
    )
    assert resposta.status_code == 404

    falhas = _eventos(
        seed["db"], acao="ver_original", resultado="falha",
        doc_id=documento.doc_id, detalhe="arquivo_ausente",
    )
    assert len(falhas) == 1


def test_parcial_sem_arquivo_gera_evento_de_falha(client, seed):
    documento = _documento_sem_arquivo(seed, seed["user_team_b"], "hash-sumido-parcial")

    resposta = client.get(
        f"/documentos/{documento.doc_id}/parcial",
        headers=_auth(seed["usuario"]),
    )
    assert resposta.status_code == 404

    falhas = _eventos(
        seed["db"], acao="ver_parcial", resultado="falha",
        doc_id=documento.doc_id, detalhe="arquivo_ausente",
    )
    assert len(falhas) == 1
