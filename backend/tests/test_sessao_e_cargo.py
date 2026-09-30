"""Identidade e papel na sessao (Fatia 4).

O frontend monta o menu por cargo. Sem o papel devolvido pelo backend, todo
usuario autenticado via em um menu vazio, porque o guarda comeca no nivel 0.
"""

from app.core.security import hash_senha

SENHA = "SenhaForte123!"


def _login(client, db, usuario):
    usuario.senha_hash = hash_senha(SENHA)
    db.commit()
    resp = client.post(
        "/auth/login", json={"email": usuario.email, "senha_hash": SENHA}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_login_devolve_identidade_e_cargo(client, seed):
    usuario = seed["usuario"]

    dados = _login(client, seed["db"], usuario)

    assert dados["access_token"]
    # O nome vem do cadastro, e nao do prefixo do e-mail.
    assert dados["user"]["nome"] == "Ana"
    assert dados["user"]["user_id"] == usuario.user_id
    # A e lider na equipe A e membro na equipe B: vale o maior nivel.
    assert dados["user"]["cargo"] == "lider"
    assert dados["user"]["nivel"] == 3


def test_login_sem_equipe_devolve_sem_cargo(client, seed):
    from app.models.usuario_equipe import UsuarioEquipe

    usuario = seed["usuario"]
    seed["db"].query(UsuarioEquipe).filter(UsuarioEquipe.user_id == usuario.user_id).delete()
    seed["db"].commit()

    dados = _login(client, seed["db"], usuario)

    assert dados["user"]["cargo"] is None
    assert dados["user"]["nivel"] == 0


def test_me_devolve_identidade_com_token(client, seed):
    usuario = seed["usuario"]
    token = _login(client, seed["db"], usuario)["access_token"]

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["nome"] == "Ana"
    assert resp.json()["cargo"] == "lider"


def test_me_exige_token(client, seed):
    resp = client.get("/auth/me")

    assert resp.status_code == 401


def test_me_rejeita_token_de_usuario_removido(client, seed):
    usuario = seed["usuario"]
    token = _login(client, seed["db"], usuario)["access_token"]
    seed["db"].delete(usuario)
    seed["db"].commit()

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401


def test_login_falha_nao_revela_dados_do_usuario(client, seed):
    resp = client.post(
        "/auth/login",
        json={"email": seed["usuario"].email, "senha_hash": "senha-errada"},
    )

    assert resp.status_code == 401
    assert "user" not in resp.json()


def test_cadastro_devolve_identidade_com_cargo_de_lider(client, seed):
    resp = client.post(
        "/auth/cadastro",
        json={
            "nome": "Bruno Alves",
            "email": "bruno@safemask.example.com",
            "senha_hash": SENHA,
        },
    )

    assert resp.status_code == 201, resp.text
    # O cadastro cria a equipe inicial e vincula o usuario como lider, entao o
    # menu ja abre com as acoes de lider e nao vazio.
    assert resp.json()["user"]["nome"] == "Bruno Alves"
    assert resp.json()["user"]["cargo"] == "lider"
