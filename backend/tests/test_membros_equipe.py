"""Adicionar e remover membros de uma equipe existente.

So o lider gerencia; a pessoa precisa ser da mesma organizacao; o ultimo
lider e o membro com documentos nao saem; cada operacao (e cada recusa por
permissao) entra na trilha. Trazido do PI-III (CAMPUSCEUB/SafeMask#85).
"""

from app.core.security import criar_token_jwt
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _pessoa(seed, nome, organizacao=None):
    db = seed["db"]
    usuario = Usuario(
        nome=nome, email=f"{nome.lower()}@safemask.example.com", senha_hash="x",
        organizacao_id=(organizacao or seed["organizacao"]).organizacao_id,
    )
    db.add(usuario)
    db.commit()
    return usuario


def _membros(client, usuario, team_id):
    return {m["email"]: m["cargo_nome"] for m in client.get(f"/equipes/{team_id}", headers=_auth(usuario)).json()["membros_lista"]}


def test_lider_adiciona_por_email_no_cargo_de_membro(client, seed):
    caio = _pessoa(seed, "Caio")
    team = seed["equipe_a"].team_id

    resp = client.post(f"/equipes/{team}/membros", headers=_auth(seed["usuario"]), json={"email": "CAIO@safemask.example.com"})

    assert resp.status_code == 201, resp.text
    assert _membros(client, seed["usuario"], team)[caio.email] == "membro"
    evento = seed["db"].query(LogAuditoria).filter_by(acao="adicionar_membro").one()
    assert (evento.team_id, evento.alvo_user_id, evento.resultado) == (team, caio.user_id, "sucesso")


def test_email_de_outra_organizacao_e_tratado_como_inexistente(client, seed):
    resp = client.post(
        f"/equipes/{seed['equipe_a'].team_id}/membros",
        headers=_auth(seed["usuario"]), json={"email": seed["usuario_globex"].email},
    )
    assert resp.status_code == 404


def test_quem_ja_e_membro_responde_409(client, seed):
    resp = client.post(
        f"/equipes/{seed['equipe_a'].team_id}/membros",
        headers=_auth(seed["usuario"]), json={"email": seed["usuario"].email},
    )
    assert resp.status_code == 409


def test_membro_comum_nao_gerencia_e_a_recusa_entra_na_trilha(client, seed):
    # Ana e membro da Equipe B.
    caio = _pessoa(seed, "Caio")
    team = seed["equipe_b"].team_id

    resp = client.post(f"/equipes/{team}/membros", headers=_auth(seed["usuario"]), json={"email": caio.email})

    assert resp.status_code == 403
    negado = seed["db"].query(LogAuditoria).filter_by(acao="adicionar_membro", resultado="negado").one()
    assert negado.team_id == team


def test_outra_organizacao_recebe_404(client, seed):
    resp = client.delete(
        f"/equipes/{seed['equipe_a'].team_id}/membros/{seed['usuario'].user_id}",
        headers=_auth(seed["usuario_globex"]),
    )
    assert resp.status_code == 404
    assert seed["db"].query(LogAuditoria).count() == 0


def test_lider_remove_membro(client, seed):
    caio = _pessoa(seed, "Caio")
    team = seed["equipe_a"].team_id
    client.post(f"/equipes/{team}/membros", headers=_auth(seed["usuario"]), json={"email": caio.email})

    resp = client.delete(f"/equipes/{team}/membros/{caio.user_id}", headers=_auth(seed["usuario"]))

    assert resp.status_code == 200, resp.text
    assert caio.email not in _membros(client, seed["usuario"], team)
    evento = seed["db"].query(LogAuditoria).filter_by(acao="remover_membro").one()
    assert evento.alvo_user_id == caio.user_id


def test_ultimo_lider_nao_sai(client, seed):
    team = seed["equipe_a"].team_id
    resp = client.delete(f"/equipes/{team}/membros/{seed['usuario'].user_id}", headers=_auth(seed["usuario"]))
    assert resp.status_code == 400


def test_membro_com_documentos_nao_sai(client, seed, documento):
    db = seed["db"]
    caio = _pessoa(seed, "Caio")
    team = seed["equipe_a"].team_id
    vinculo = UsuarioEquipe(user_id=caio.user_id, team_id=team, cargo_id=seed["cargo_membro"].cargo_id)
    db.add(vinculo)
    db.flush()
    db.add(documento(vinculo.user_team_id))
    db.commit()

    resp = client.delete(f"/equipes/{team}/membros/{caio.user_id}", headers=_auth(seed["usuario"]))

    assert resp.status_code == 409
    assert "1 documento" in resp.json()["detail"]


def test_detalhe_diz_quem_pode_gerenciar(client, seed):
    lider = client.get(f"/equipes/{seed['equipe_a'].team_id}", headers=_auth(seed["usuario"])).json()
    membro = client.get(f"/equipes/{seed['equipe_b'].team_id}", headers=_auth(seed["usuario"])).json()
    assert lider["pode_gerenciar_membros"] is True
    assert membro["pode_gerenciar_membros"] is False
