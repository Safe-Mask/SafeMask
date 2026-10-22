"""Alterar o cargo de um membro da equipe.

So o lider altera; a equipe nunca fica sem lider; o novo cargo vale ja no
proximo acesso; a operacao entra na trilha com o alvo. Trazido do PI-III
(CAMPUSCEUB/SafeMask#86).
"""

from app.core.security import criar_token_jwt
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _membro_na_a(seed, nome="Caio", cargo="cargo_membro"):
    db = seed["db"]
    pessoa = Usuario(nome=nome, email=f"{nome.lower()}@safemask.example.com", senha_hash="x",
                     organizacao_id=seed["organizacao"].organizacao_id)
    db.add(pessoa)
    db.flush()
    db.add(UsuarioEquipe(user_id=pessoa.user_id, team_id=seed["equipe_a"].team_id, cargo_id=seed[cargo].cargo_id))
    db.commit()
    return pessoa


def _cargo_de(client, seed, pessoa):
    detalhe = client.get(f"/equipes/{seed['equipe_a'].team_id}", headers=_auth(seed["usuario"])).json()
    return next(m["cargo_nome"] for m in detalhe["membros_lista"] if m["user_id"] == pessoa.user_id)


def _alterar(client, seed, quem, alvo, cargo, team=None):
    team = team or seed["equipe_a"].team_id
    return client.patch(f"/equipes/{team}/membros/{alvo.user_id}", headers=_auth(quem), json={"cargo": cargo})


def test_lider_promove_membro_a_supervisor(client, seed):
    caio = _membro_na_a(seed)

    resp = _alterar(client, seed, seed["usuario"], caio, "supervisor")

    assert resp.status_code == 200, resp.text
    assert _cargo_de(client, seed, caio) == "supervisor"
    evento = seed["db"].query(LogAuditoria).filter_by(acao="alterar_cargo").one()
    assert (evento.alvo_user_id, evento.cargo_id) == (caio.user_id, seed["cargo_lider"].cargo_id)


def test_nome_do_cargo_nao_diferencia_maiusculas(client, seed):
    caio = _membro_na_a(seed)
    assert _alterar(client, seed, seed["usuario"], caio, "  Supervisor ").status_code == 200


def test_cargo_inexistente_ou_igual_responde_400(client, seed):
    caio = _membro_na_a(seed)
    assert _alterar(client, seed, seed["usuario"], caio, "diretor").status_code == 400
    assert _alterar(client, seed, seed["usuario"], caio, "membro").status_code == 400


def test_ultimo_lider_nao_e_rebaixado(client, seed):
    resp = _alterar(client, seed, seed["usuario"], seed["usuario"], "membro")
    assert resp.status_code == 400


def test_com_outro_lider_o_lider_pode_se_rebaixar(client, seed):
    _membro_na_a(seed, "Bruno", cargo="cargo_lider")
    assert _alterar(client, seed, seed["usuario"], seed["usuario"], "membro").status_code == 200


def test_quem_nao_e_lider_recebe_403_e_negado_na_trilha(client, seed):
    # Ana e membro na Equipe B.
    db = seed["db"]
    lider_b = Usuario(nome="Lia", email="lia@safemask.example.com", senha_hash="x",
                      organizacao_id=seed["organizacao"].organizacao_id)
    db.add(lider_b)
    db.flush()
    db.add(UsuarioEquipe(user_id=lider_b.user_id, team_id=seed["equipe_b"].team_id, cargo_id=seed["cargo_lider"].cargo_id))
    db.commit()

    resp = _alterar(client, seed, seed["usuario"], lider_b, "membro", team=seed["equipe_b"].team_id)

    assert resp.status_code == 403
    assert db.query(LogAuditoria).filter_by(acao="alterar_cargo", resultado="negado").count() == 1


def test_detalhe_traz_os_cargos_para_o_seletor(client, seed):
    detalhe = client.get(f"/equipes/{seed['equipe_a'].team_id}", headers=_auth(seed["usuario"])).json()
    assert [c["nome"] for c in detalhe["cargos"]] == ["lider", "supervisor", "membro"]
