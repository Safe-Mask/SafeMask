"""Consulta da trilha de auditoria (GET /auditoria).

Lider e supervisor veem os eventos das proprias equipes, da propria
organizacao; membro comum e outra organizacao recebem 403. Trazido do PI-III
(CAMPUSCEUB/SafeMask#13).
"""

from datetime import datetime, timedelta

from app.core.security import criar_token_jwt
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _evento(db, user_id, team_id, acao="ver_censurado", resultado="sucesso", quando=None, doc_id=None):
    evento = LogAuditoria(
        user_id=user_id, team_id=team_id, acao=acao, ip_origem="1.2.3.4",
        resultado=resultado, doc_id=doc_id, data_hora=quando or datetime(2026, 10, 20, 12, 0, 0),
    )
    db.add(evento)
    db.commit()
    return evento


def test_lider_ve_os_eventos_da_propria_equipe_do_mais_recente(client, seed):
    db, ana = seed["db"], seed["usuario"]
    antigo = _evento(db, ana.user_id, seed["equipe_a"].team_id, quando=datetime(2026, 10, 1, 9))
    novo = _evento(db, ana.user_id, seed["equipe_a"].team_id, acao="ver_original", resultado="negado",
                   quando=datetime(2026, 10, 2, 9))

    resp = client.get("/auditoria", headers=_auth(ana))

    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    assert [e["log_id"] for e in corpo["eventos"]] == [novo.log_id, antigo.log_id]
    assert corpo["eventos"][0]["resultado"] == "negado"
    assert corpo["eventos"][0]["data_hora"] == "2026-10-02T09:00:00+00:00"
    assert corpo["eventos"][0]["equipe"]["nome"] == "Equipe A"


def test_eventos_de_equipe_em_que_e_membro_nao_aparecem(client, seed):
    # Ana e lider da A e membro da B.
    db, ana = seed["db"], seed["usuario"]
    _evento(db, ana.user_id, seed["equipe_b"].team_id)

    assert client.get("/auditoria", headers=_auth(ana)).json()["total"] == 0
    resp = client.get(f"/auditoria?team_id={seed['equipe_b'].team_id}", headers=_auth(ana))
    assert resp.status_code == 403


def test_membro_comum_nao_consulta(client, seed):
    db = seed["db"]
    so_membro = Usuario(nome="Duda", email="duda@safemask.example.com", senha_hash="x",
                        organizacao_id=seed["organizacao"].organizacao_id)
    db.add(so_membro)
    db.flush()
    db.add(UsuarioEquipe(user_id=so_membro.user_id, team_id=seed["equipe_a"].team_id,
                         cargo_id=seed["cargo_membro"].cargo_id))
    db.commit()

    assert client.get("/auditoria", headers=_auth(so_membro)).status_code == 403


def test_outra_organizacao_nao_ve_os_eventos(client, seed):
    db = seed["db"]
    _evento(db, seed["usuario"].user_id, seed["equipe_a"].team_id)

    resp = client.get("/auditoria", headers=_auth(seed["usuario_globex"]))

    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    resp = client.get(f"/auditoria?team_id={seed['equipe_a'].team_id}", headers=_auth(seed["usuario_globex"]))
    assert resp.status_code == 403


def test_filtros_por_acao_periodo_e_paginacao(client, seed):
    db, ana = seed["db"], seed["usuario"]
    base = datetime(2026, 10, 10, 12)
    for i in range(5):
        _evento(db, ana.user_id, seed["equipe_a"].team_id, acao="ver_parcial", quando=base + timedelta(hours=i))
    _evento(db, ana.user_id, seed["equipe_a"].team_id, acao="upload_documento", quando=base)

    por_acao = client.get("/auditoria?acao=upload_documento", headers=_auth(ana)).json()
    assert por_acao["total"] == 1

    periodo = client.get(
        "/auditoria?data_inicio=2026-10-10T13:00:00&data_fim=2026-10-10T15:00:00", headers=_auth(ana)
    ).json()
    assert periodo["total"] == 3

    pagina = client.get("/auditoria?por_pagina=2&pagina=3", headers=_auth(ana)).json()
    assert pagina["paginas"] == 3 and len(pagina["eventos"]) == 2


def test_filtro_invalido_responde_400(client, seed):
    ana = seed["usuario"]
    assert client.get("/auditoria?acao=apagar_tudo", headers=_auth(ana)).status_code == 400
    resp = client.get("/auditoria?data_inicio=2026-10-10T00:00:00&data_fim=2026-10-01T00:00:00", headers=_auth(ana))
    assert resp.status_code == 400


def test_filtro_por_documento_de_outra_equipe_e_recusado(client, seed, documento):
    db = seed["db"]
    doc_b = documento(seed["user_team_b"])
    db.add(doc_b)
    db.commit()

    resp = client.get(f"/auditoria?doc_id={doc_b.doc_id}", headers=_auth(seed["usuario"]))

    assert resp.status_code == 403
