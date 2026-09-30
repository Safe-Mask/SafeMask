"""Regressoes de seguranca do fluxo de documentos.

Bug de origem: ao compartilhar um PDF com varias equipes, `upload_documento`
cria um registro de `Documento` por equipe, mas o scanner so grava
`DadoSensivel` no primeiro. Um membro da segunda equipe abria
`/documentos/{doc_id}/parcial`, nao encontrava nenhum item e recebia o PDF
ORIGINAL sem censura.
"""

import pytest

from app.core.security import criar_token_jwt
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from tests.conftest import CONTEUDO_PDF

TOKEN = criar_token_jwt({"sub": "ana@safemask.example.com", "nome": "Ana"})
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _upload(client, teams, conteudo=CONTEUDO_PDF):
    return client.post(
        "/documentos/upload",
        headers=AUTH,
        files={"file": ("contrato.pdf", conteudo, "application/pdf")},
        data={"titulo": "Contrato", "nivel_seguranca": "1", "teams": teams},
    )


# --- Regressao 1: dados sensiveis precisam ser compartilhados --------------


def test_dados_sensiveis_sao_compartilhados_com_todas_as_equipes(
    client, seed, scanner_registrado, tmp_path
):
    """Todo Documento de um upload multi-equipe deve ter os mesmos itens."""
    db = seed["db"]
    scanner_registrado([(3, 1), (3, 1), (2, 2)])

    resp = _upload(client, f"[{seed['equipe_a'].team_id}, {seed['equipe_b'].team_id}]")
    assert resp.status_code == 201, resp.text

    docs = db.query(Documento).all()
    assert len(docs) == 2

    por_doc = {}
    for doc in docs:
        itens = db.query(DadoSensivel).filter(DadoSensivel.doc_id == doc.doc_id).all()
        por_doc[doc.doc_id] = sorted((i.tipo_entidade, i.nivel_requerido, i.pagina) for i in itens)

    assert por_doc[docs[0].doc_id] == [("CPF", 2, 2), ("CPF", 3, 1), ("CPF", 3, 1)]
    # Esta e a regressao: o segundo Documento nao pode ficar sem nenhum item,
    # senao /parcial responde com o PDF original.
    assert por_doc[docs[1].doc_id] == por_doc[docs[0].doc_id]


def test_parcial_nao_vaza_original_em_documento_compartilhado(
    client, seed, scanner_registrado, tmp_path
):
    """Membro da segunda equipe nunca recebe o PDF original."""
    db = seed["db"]
    scanner_registrado([(3, 1)])

    resp = _upload(client, f"[{seed['equipe_a'].team_id}, {seed['equipe_b'].team_id}]")
    assert resp.status_code == 201, resp.text

    docs = db.query(Documento).order_by(Documento.doc_id).all()
    doc_equipe_b = docs[1]
    assert doc_equipe_b.user_team_id == seed["user_team_b"]

    # Grava o original em disco como o upload faria.
    import hashlib

    hash_documento = hashlib.sha256(CONTEUDO_PDF).hexdigest()
    (tmp_path / "originais" / f"{hash_documento}.pdf").write_bytes(CONTEUDO_PDF)

    resp = client.get(f"/documentos/{doc_equipe_b.doc_id}/parcial", headers=AUTH)

    assert resp.status_code == 200, resp.text
    assert resp.content != CONTEUDO_PDF, "endpoint /parcial devolveu o PDF original sem censura"


# --- Regressao 2: documento sem itens nunca expoe o original --------------


def test_parcial_nao_expoe_original_quando_documento_nao_tem_itens(
    client, seed, scanner_registrado, tmp_path
):
    """Scan que nao encontrou nada nao pode autorizar o original.

    Usa a equipe B, onde Ana e `membro` (nivel 1): o cargo nao tem direito a
    descensura, entao qualquer original servido aqui e um vazamento.
    """
    db = seed["db"]
    scanner_registrado([])

    resp = _upload(client, f"[{seed['equipe_b'].team_id}]")
    assert resp.status_code == 201, resp.text

    import hashlib

    hash_documento = hashlib.sha256(CONTEUDO_PDF).hexdigest()
    (tmp_path / "originais" / f"{hash_documento}.pdf").write_bytes(CONTEUDO_PDF)

    doc = db.query(Documento).one()
    resp = client.get(f"/documentos/{doc.doc_id}/parcial", headers=AUTH)

    assert resp.status_code == 200, resp.text
    assert resp.content != CONTEUDO_PDF, "documento sem dados sensiveis devolveu o original"


def test_parcial_de_lider_ainda_recebe_o_original(client, seed, scanner_registrado, tmp_path):
    """Descensura de nivel 3+ continua entregando o original."""
    db = seed["db"]
    scanner_registrado([(3, 1)])

    resp = _upload(client, f"[{seed['equipe_a'].team_id}]")
    assert resp.status_code == 201, resp.text

    import hashlib

    hash_documento = hashlib.sha256(CONTEUDO_PDF).hexdigest()
    (tmp_path / "originais" / f"{hash_documento}.pdf").write_bytes(CONTEUDO_PDF)

    doc = db.query(Documento).one()
    resp = client.get(f"/documentos/{doc.doc_id}/parcial", headers=AUTH)

    assert resp.status_code == 200, resp.text
    assert resp.content == CONTEUDO_PDF
