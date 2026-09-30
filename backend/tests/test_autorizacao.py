"""Autorizacao por cargo e escopo de tenant (Fatia 5b).

Os casos vem de bugs reais do codigo, nao de cobertura generica:

1. `cargo_usuario_no_documento` resolvia o `team_id` pelo primeiro membro do
   vinculo sem comparar organizacao, e comparava nivel na mao em cada rota.
2. `create_team` aceitava qualquer autenticado: um membro comum criava um
   time e nascia lider, destravando descensura sobre os proprios documentos.
"""

import pytest
from fastapi import HTTPException

from app.core.autorizacao import (
    NIVEL_LIDER,
    NIVEL_SUPERVISOR,
    cargo_na_equipe,
    exigir_gestao,
    maior_cargo,
)
from app.core.security import criar_token_jwt
from app.models.cargo import Cargo
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _auth(usuario) -> dict:
    token = criar_token_jwt({"sub": usuario.email, "nome": usuario.nome})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def membro_puro(db_session, seed):
    """Usuario da Acme que so e `membro` na Equipe A.

    A conta que importa para o teste: nao supervisa, nao lidera, e mesmo
    assim mora na mesma organizacao que Ana.
    """
    equipe = Equipe(
        nome="Equipe C",
        descricao="so membros",
        organizacao_id=seed["organizacao"].organizacao_id,
    )
    usuario = Usuario(
        nome="Cid",
        email="cid@safemask.example.com",
        senha_hash=seed["usuario"].senha_hash,
        organizacao_id=seed["organizacao"].organizacao_id,
    )
    db_session.add_all([equipe, usuario])
    db_session.flush()
    vinculo = UsuarioEquipe(
        user_id=usuario.user_id,
        team_id=equipe.team_id,
        cargo_id=seed["cargo_membro"].cargo_id,
    )
    db_session.add(vinculo)
    db_session.commit()
    db_session.refresh(usuario)
    return {"usuario": usuario, "equipe": equipe, "vinculo": vinculo}


@pytest.fixture
def documento_de_ana(db_session, seed):
    """Documento pertencente a Equipe A, onde Ana e lider."""
    documento = Documento(
        user_team_id=seed["user_team_a"],
        nome_original="ata.pdf",
        extensao=".pdf",
        tamanho_bytes=10,
        nivel_seguranca=1,
        chave_criptografica="k",
        hash_documento=f"doc-autorizacao-{seed['equipe_a'].team_id}",
        caminho_storage="/tmp/doc.pdf",
        status_processamento="CONCLUIDO",
        ativo=True,
    )
    db_session.add(documento)
    db_session.commit()
    db_session.refresh(documento)
    return documento


# --- cargo_na_equipe / maior_cargo -------------------------------------------


def test_cargo_na_equipe_usa_o_vinculo_certo(seed):
    """Ana e lider na A e membro na B: o cargo depende da equipe, nao do token."""
    assert cargo_na_equipe(seed["db"], seed["usuario"], seed["equipe_a"].team_id)["nivel"] == NIVEL_LIDER
    assert cargo_na_equipe(seed["db"], seed["usuario"], seed["equipe_b"].team_id)["nivel"] == 1


def test_cargo_na_equipe_rejeita_equipe_de_outro_tenant(seed):
    """Bia e lider da Globex, mas nao da Acme: o filtro de org barra."""
    cargo = cargo_na_equipe(seed["db"], seed["usuario_globex"], seed["equipe_a"].team_id)
    assert cargo is None


def test_maior_cargo_pega_o_mais_alto_dentro_do_tenant(seed):
    """Ana e membro na B e lider na A; o cargo efetivo e o maior."""
    assert maior_cargo(seed["db"], seed["usuario"])["nivel"] == NIVEL_LIDER


def test_maior_cargo_de_usuario_sem_organizacao_e_403(seed):
    """Conta sem tenant nao recebe cargo: 403, nao um cargo herdado."""
    usuario = Usuario(
        nome="Sem Org",
        email="semorg@safemask.example.com",
        senha_hash=seed["usuario"].senha_hash,
        organizacao_id=None,
    )
    seed["db"].add(usuario)
    seed["db"].commit()

    with pytest.raises(HTTPException) as exc:
        maior_cargo(seed["db"], usuario)
    assert exc.value.status_code == 403


# --- criar equipe exige gestao ------------------------------------------------


def test_membro_comum_nao_cria_equipe(client, seed, membro_puro):
    """Regressao: antes, um membro criava o time e ja nascia lider."""
    resp = client.post(
        "/equipes",
        json={"nome": "Time do Cid", "descricao": None, "membros_ids": []},
        headers=_auth(membro_puro["usuario"]),
    )
    assert resp.status_code == 403, resp.text


def test_membro_comum_nao_vira_lider_mesmo_com_403(client, seed, membro_puro):
    """A recusa nao pode deixar equipe orfa pela metade."""
    client.post(
        "/equipes",
        json={"nome": "Time do Cid", "descricao": None, "membros_ids": []},
        headers=_auth(membro_puro["usuario"]),
    )
    times = (
        seed["db"].query(Equipe).filter(Equipe.nome == "Time do Cid").all()
    )
    assert times == []


def test_lider_cria_equipe_e_vira_lider(client, seed):
    """Caminho feliz preservado: lider cria e lidera."""
    resp = client.post(
        "/equipes",
        json={"nome": "Time Novo", "descricao": "d", "membros_ids": []},
        headers=_auth(seed["usuario"]),
    )
    assert resp.status_code == 201, resp.text


def test_exigir_gestao_aceita_supervisor(db_session, seed):
    """Supervisor (nivel 2) basta; o piso e supervisao, nao lideranca."""
    supervisor = Usuario(
        nome="Dora",
        email="dora@safemask.example.com",
        senha_hash=seed["usuario"].senha_hash,
        organizacao_id=seed["organizacao"].organizacao_id,
    )
    db_session.add(supervisor)
    db_session.flush()
    db_session.add(
        UsuarioEquipe(
            user_id=supervisor.user_id,
            team_id=seed["equipe_b"].team_id,
            cargo_id=seed["cargo_supervisor"].cargo_id,
        )
    )
    db_session.commit()

    cargo = exigir_gestao(db_session, supervisor)

    assert cargo["nome"] == "supervisor"
    assert cargo["nivel"] == NIVEL_SUPERVISOR


# --- documentos: escopo e nivel ----------------------------------------------


def test_documento_de_outro_tenant_responde_404(client, seed, documento_de_ana):
    """Bia nao recebe 403: 403 confirmaria que o documento existe."""
    resp = client.get(
        f"/documentos/censurados/{documento_de_ana.doc_id}",
        headers=_auth(seed["usuario_globex"]),
    )
    assert resp.status_code == 404, resp.text


def test_lider_em_uma_equipe_nao_descensura_em_outra(client, seed, documento_de_ana):
    """Regressao de escopo: Ana e lider na A e *membro* na B.

    Se o cargo viesse do token em vez do vinculo com a equipe dona do
    documento, Ana veria o original da Equipe B.
    """
    documento_de_ana.user_team_id = seed["user_team_b"]
    seed["db"].commit()
    headers = _auth(seed["usuario"])

    detalhe = client.get(f"/documentos/censurados/{documento_de_ana.doc_id}", headers=headers)
    assert detalhe.status_code == 200, detalhe.text
    assert detalhe.json()["pode_descensurar"] is False

    original = client.get(f"/documentos/{documento_de_ana.doc_id}/original", headers=headers)
    assert original.status_code == 403, original.text


def test_membro_puro_nao_acessa_original(client, seed, membro_puro, documento_de_ana):
    """Documento da Equipe C, onde Cid so e membro: 403 no original."""
    documento_de_ana.user_team_id = membro_puro["vinculo"].user_team_id
    seed["db"].commit()
    headers = _auth(membro_puro["usuario"])

    detalhe = client.get(f"/documentos/censurados/{documento_de_ana.doc_id}", headers=headers)
    assert detalhe.status_code == 200, detalhe.text
    assert detalhe.json()["pode_descensurar"] is False

    original = client.get(f"/documentos/{documento_de_ana.doc_id}/original", headers=headers)
    assert original.status_code == 403, original.text
