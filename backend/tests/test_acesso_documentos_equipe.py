"""Pagina da equipe libera os documentos para todo membro da equipe.

`tem_acesso` era verdadeiro so para o documento enviado pelo proprio usuario:
o lider e os demais membros viam "Bloqueado" em tudo o que outro membro
enviou, embora as rotas de documento liberem o acesso conforme o cargo.
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#180).
"""

from app.core.security import criar_token_jwt
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe


def _auth(usuario):
    token = criar_token_jwt({"sub": usuario.email, "nome": usuario.nome})
    return {"Authorization": f"Bearer {token}"}


def _documento_de_outro_membro(seed, documento):
    """Carlos (lider da Equipe B) envia um documento; Ana e membro da B."""
    db = seed["db"]
    carlos = Usuario(
        nome="Carlos",
        email="carlos@safemask.example.com",
        senha_hash="x",
        organizacao_id=seed["organizacao"].organizacao_id,
    )
    db.add(carlos)
    db.flush()
    vinculo = UsuarioEquipe(
        user_id=carlos.user_id,
        team_id=seed["equipe_b"].team_id,
        cargo_id=seed["cargo_lider"].cargo_id,
    )
    db.add(vinculo)
    db.flush()
    doc = documento(vinculo.user_team_id)
    db.add(doc)
    db.commit()
    return carlos, doc


def _na_pagina(client, usuario, team_id, doc_id):
    resp = client.get(f"/equipes/{team_id}", headers=_auth(usuario))
    assert resp.status_code == 200, resp.text
    return next(d for d in resp.json()["documentos_lista"] if d["doc_id"] == doc_id)


def test_membro_acessa_documento_enviado_por_outro_membro(client, seed, documento):
    _, doc = _documento_de_outro_membro(seed, documento)

    item = _na_pagina(client, seed["usuario"], seed["equipe_b"].team_id, doc.doc_id)

    assert item["tem_acesso"] is True
    assert item["preview_url"] == f"/documentos/censurados/{doc.doc_id}/arquivo"


def test_quem_enviou_continua_com_acesso(client, seed, documento):
    carlos, doc = _documento_de_outro_membro(seed, documento)

    item = _na_pagina(client, carlos, seed["equipe_b"].team_id, doc.doc_id)

    assert item["tem_acesso"] is True


def test_usuario_de_fora_da_equipe_nao_ve_a_pagina(client, seed, documento):
    _, doc = _documento_de_outro_membro(seed, documento)

    resp = client.get(f"/equipes/{seed['equipe_b'].team_id}", headers=_auth(seed["usuario_globex"]))

    assert resp.status_code == 404
