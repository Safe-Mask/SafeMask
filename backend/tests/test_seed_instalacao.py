"""Seed de instalacao (org unica + admin + equipe padrao) e o reforco de
troca de senha que acompanha o admin provisorio."""

from app.core import seed_instalacao
from app.core.security import verificar_senha
from app.models import Cargo, Equipe, Usuario, UsuarioEquipe


def _sessoes_de_teste(db_session):
    """SessionLocal do middleware apontando para o banco limpo do teste."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core import troca_senha

    sessoes = sessionmaker(
        autocommit=False, autoflush=False,
        bind=create_engine(
            db_session.get_bind().url,
            connect_args={"check_same_thread": False},
        ),
    )
    return troca_senha, sessoes


def _cargos(db_session):
    lider = Cargo(nome="lider", nivel=3, descricao="lider")
    db_session.add_all([
        lider,
        Cargo(nome="supervisor", nivel=2, descricao="supervisor"),
    ])
    db_session.commit()
    return lider


def test_semear_cria_admin_equipe_e_org_unica(db_session):
    admin = seed_instalacao.semear(
        db_session, senha_inicial="SenhaProvisoria12!"
    )

    assert admin is not None
    assert admin.email == seed_instalacao.ADMIN_EMAIL_PADRAO
    assert admin.precisa_trocar_senha is True
    assert verificar_senha("SenhaProvisoria12!", admin.senha_hash)

    assert admin.organizacao.nome  # organizacao unica vinculada

    vinculo = (
        db_session.query(UsuarioEquipe)
        .filter(UsuarioEquipe.user_id == admin.user_id)
        .one()
    )
    equipe = db_session.get(Equipe, vinculo.team_id)
    assert equipe.nome == seed_instalacao.EQUIPE_PADRAO_SEED_NOME
    cargo = db_session.get(Cargo, vinculo.cargo_id)
    assert cargo.nome == "lider"

    # Idempotente: segunda chamada nao cria nada.
    assert seed_instalacao.semear(db_session, senha_inicial="Outra12!") is None
    assert db_session.query(Usuario).count() == 1


def test_senha_inicial_aleatoria_e_usavel_no_primeiro_acesso():
    for _ in range(5):
        senha = seed_instalacao.senha_inicial_nova()
        assert len(senha) >= 16
        # urlsafe nao gera caracteres ambigos de copia/cola
        assert not any(c in senha for c in "'\"\\ ")


def test_admin_provisorio_e_travado_ate_a_troca_de_senha(db_session, client, monkeypatch):
    seed_instalacao.semear(db_session, senha_inicial="SenhaProvisoria12!")
    db_session.commit()
    troca_senha, sessoes = _sessoes_de_teste(db_session)
    monkeypatch.setattr(troca_senha, "SessionLocal", sessoes)

    login = client.post("/auth/login", json={
        "email": seed_instalacao.ADMIN_EMAIL_PADRAO,
        "senha_hash": "SenhaProvisoria12!",
    })
    assert login.status_code == 200, login.text
    corpo = login.json()
    assert corpo["user"]["precisa_trocar_senha"] is True
    cabecalho = {"Authorization": f"Bearer {corpo['access_token']}"}

    # A API inteira fica trancada ate a troca.
    travado = client.get("/equipes/overview", headers=cabecalho)
    assert travado.status_code == 403
    assert "Troque a senha" in travado.json()["detail"]
    assert client.get("/auth/me", headers=cabecalho).status_code == 200

    # Troca recusa a senha atual errada e o travamento continua.
    errada = client.post("/auth/trocar-senha", headers=cabecalho, json={
        "senha_atual": "Errada123!", "nova_senha": "NovaSenhaForte9!"
    })
    assert errada.status_code == 400
    assert client.get("/equipes/overview", headers=cabecalho).status_code == 403

    ok = client.post("/auth/trocar-senha", headers=cabecalho, json={
        "senha_atual": "SenhaProvisoria12!", "nova_senha": "NovaSenhaForte9!"
    })
    assert ok.status_code == 200, ok.text
    token_novo = ok.json()["access_token"]
    assert ok.json()["user"]["precisa_trocar_senha"] is False

    liberado = client.get(
        "/equipes/overview", headers={"Authorization": f"Bearer {token_novo}"}
    )
    assert liberado.status_code == 200, liberado.text


def test_middleware_so_bloqueia_fora_de_auth_e_options(db_session, client, monkeypatch):
    """Rotinas de auth (e OPTIONS preflight) ficam abertas mesmo com o banco
    inteiro travado: quem ainda nao tem senha provisoria tambem precisa
    conseguir entrar para trocar a propria."""
    _cargos(db_session)
    troca_senha, sessoes = _sessoes_de_teste(db_session)
    monkeypatch.setattr(troca_senha, "SessionLocal", sessoes)

    cadastro = client.post("/auth/cadastro", json={
        "nome": "Novo Usuario", "email": "novo@safemask.example.com",
        "senha_hash": "SenhaForte123!",
    })
    assert cadastro.status_code == 201, cadastro.text

    token = cadastro.json()["access_token"]
    cabecalho = {"Authorization": f"Bearer {token}"}
    assert client.get("/equipes/overview", headers=cabecalho).status_code == 200

    options = client.options("/equipes/overview")
    assert options.status_code != 403
