"""Contadores do overview de equipes.

A consulta filtrava `usuario_equipe` pelo proprio usuario e contava sobre essa
juncao: cada equipe aparecia com 1 membro e so com os documentos enviados pelo
proprio usuario. Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#61).
"""

from app.core.security import criar_token_jwt
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def test_overview_conta_todos_os_membros_e_documentos_da_equipe(client, seed, documento):
    db = seed["db"]
    carlos = Usuario(
        nome="Carlos", email="carlos@safemask.example.com", senha_hash="x",
        organizacao_id=seed["organizacao"].organizacao_id,
    )
    db.add(carlos)
    db.flush()
    vinculo = UsuarioEquipe(
        user_id=carlos.user_id, team_id=seed["equipe_a"].team_id, cargo_id=seed["cargo_membro"].cargo_id,
    )
    db.add(vinculo)
    db.flush()
    db.add_all([documento(vinculo.user_team_id), documento(seed["user_team_a"], hash_documento="outro")])
    db.commit()

    resp = client.get("/equipes/overview", headers=_auth(seed["usuario"]))
    assert resp.status_code == 200, resp.text
    equipe_a = next(e for e in resp.json()["equipes"] if e["team_id"] == seed["equipe_a"].team_id)

    assert equipe_a["membros"] == 2
    assert equipe_a["documentos"] == 2
    assert equipe_a["cargo_nivel_usuario"] == 3

    equipe_b = next(e for e in resp.json()["equipes"] if e["team_id"] == seed["equipe_b"].team_id)
    assert equipe_b["cargo_nivel_usuario"] == 1


def test_overview_bate_com_a_pagina_de_detalhe(client, seed, documento):
    db = seed["db"]
    db.add(documento(seed["user_team_a"]))
    db.commit()

    overview = client.get("/equipes/overview", headers=_auth(seed["usuario"])).json()
    for equipe in overview["equipes"]:
        detalhe = client.get(f"/equipes/{equipe['team_id']}", headers=_auth(seed["usuario"])).json()
        assert equipe["membros"] == detalhe["membros"]
        assert equipe["documentos"] == detalhe["documentos"]
