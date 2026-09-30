"""Isolamento por organizacao (Fatia 5a).

A organizacao e o limite de dados. Estes testes usam duas organizacoes do
fixture `seed` (Acme, onde esta Ana, e Globex, onde esta Bia) e verificam que
nada da Acme aparece para um usuario da Globex, nem o contrario.
"""

from app.core.security import criar_token_jwt

SENHA = "SenhaForte123!"


def _auth(usuario):
    token = criar_token_jwt({"sub": usuario.email, "nome": usuario.nome})
    return {"Authorization": f"Bearer {token}"}


def _login(client, db, usuario):
    from app.core.security import hash_senha

    usuario.senha_hash = hash_senha(SENHA)
    db.commit()
    resp = client.post(
        "/auth/login", json={"email": usuario.email, "senha_hash": SENHA}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Modelo e migracao ---------------------------------------------------


def test_seed_tem_duas_organizacoes_distintas(seed):
    assert seed["organizacao"].organizacao_id != seed["organizacao_globex"].organizacao_id
    assert seed["usuario"].organizacao_id == seed["organizacao"].organizacao_id
    assert seed["equipe_a"].organizacao_id == seed["organizacao"].organizacao_id
    assert seed["equipe_globex"].organizacao_id == seed["organizacao_globex"].organizacao_id


def test_cargo_efetivo_ignora_vinculo_de_outra_organizacao(db_session, seed):
    """Um cargo alto em outra organizacao nao pode virar o papel exibido."""
    from app.routes.auth import cargo_efetivo

    db_session.add(
        seed["equipe_a"].__class__(nome="Equipe Satelite", organizacao_id=seed["organizacao_globex"].organizacao_id)
    )
    db_session.flush()
    from app.models.usuario_equipe import UsuarioEquipe

    # Ana (lider na Acme) ganha um vinculo de supervisor na Globex.
    satelite = db_session.query(seed["equipe_a"].__class__).filter_by(nome="Equipe Satelite").one()
    db_session.add(
        UsuarioEquipe(
            user_id=seed["usuario"].user_id,
            team_id=satelite.team_id,
            cargo_id=seed["cargo_supervisor"].cargo_id,
        )
    )
    db_session.commit()

    global_ = cargo_efetivo(db_session, seed["usuario"].user_id)
    restrito = cargo_efetivo(
        db_session, seed["usuario"].user_id, seed["organizacao"].organizacao_id
    )

    # Sem restricao o vinculo externo eleva o papel; restrito a Acme, nao.
    assert global_["nome"] == "lider"
    assert restrito == {"nome": "lider", "nivel": 3}


def test_identidade_traz_organizacao(client, seed):
    dados = _login(client, seed["db"], seed["usuario"])

    assert dados["user"]["organizacao_id"] == seed["organizacao"].organizacao_id
    assert dados["user"]["organizacao_nome"] == "Acme"


def test_cadastro_cria_organizacao_propria(client, seed):
    """Cada cadastro novo abre seu proprio tenant, isolado do legado."""
    resp = client.post(
        "/auth/cadastro",
        json={"nome": "Carla", "email": "carla@safemask.example.com", "senha_hash": SENHA},
    )

    assert resp.status_code == 201, resp.text
    organizacao_id = resp.json()["user"]["organizacao_id"]
    assert organizacao_id is not None
    # Nem a organizacao da Acme nem a da Globex.
    assert organizacao_id not in (
        seed["organizacao"].organizacao_id,
        seed["organizacao_globex"].organizacao_id,
    )


# --- Vazamento entre tenants ---------------------------------------------


def test_form_data_nao_sugere_usuarios_de_outra_organizacao(client, seed):
    resp = client.get("/equipes/form-data", headers=_auth(seed["usuario"]))

    assert resp.status_code == 200, resp.text
    ids = {u["user_id"] for u in resp.json()["usuarios_disponiveis"]}
    assert seed["usuario_globex"].user_id not in ids


def test_form_data_nao_sugere_nome_de_usuario_de_outra_organizacao(client, seed):
    resp = client.get("/equipes/form-data?query=Bia", headers=_auth(seed["usuario"]))

    assert resp.status_code == 200, resp.text
    assert resp.json()["usuarios_disponiveis"] == []


def test_criar_equipe_ignora_membro_de_outra_organizacao(client, seed):
    resp = client.post(
        "/equipes",
        json={
            "nome": "Equipe Nova",
            "membros_ids": [seed["usuario_globex"].user_id],
        },
        headers=_auth(seed["usuario"]),
    )

    assert resp.status_code == 201, resp.text
    membros = {m["user_id"] for m in resp.json()["equipe"]["membros_lista"]}
    assert seed["usuario_globex"].user_id not in membros
    # A equipe nasce dentro da organizacao de quem a criou.
    assert resp.json()["equipe"]["organizacao_id"] == seed["organizacao"].organizacao_id


def test_equipe_criada_pertence_a_organizacao_do_criador(db_session, client, seed):
    from app.models.equipe import Equipe

    resp = client.post(
        "/equipes",
        json={"nome": "Equipe da Acme"},
        headers=_auth(seed["usuario"]),
    )

    equipe_id = resp.json()["equipe"]["team_id"]
    equipe = db_session.query(Equipe).filter(Equipe.team_id == equipe_id).one()
    assert equipe.organizacao_id == seed["organizacao"].organizacao_id


def test_equipe_de_outra_organizacao_nao_e_acessivel(client, seed):
    resp = client.get(
        f"/equipes/{seed['equipe_globex'].team_id}", headers=_auth(seed["usuario"])
    )

    assert resp.status_code == 404


def test_overview_nao_lista_equipes_de_outra_organizacao(client, seed):
    resp = client.get("/equipes/overview", headers=_auth(seed["usuario"]))

    assert resp.status_code == 200, resp.text
    nomes = {e["nome"] for e in resp.json()["equipes"]}
    assert "Equipe Globex" not in nomes


def test_usuario_sem_organizacao_nao_acessa_a_gestao_de_equipes(client, seed):
    """Estado inconsistente deve falhar explicitamente, nao responder vazio."""
    seed["usuario"].organizacao_id = None
    seed["db"].commit()

    resp = client.get("/equipes/form-data", headers=_auth(seed["usuario"]))

    assert resp.status_code == 403
