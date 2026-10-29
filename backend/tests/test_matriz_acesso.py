"""Matriz de acesso por cargo, celula por celula.

Versao do documento x nivel do cargo (membro 1, supervisor 2, lider 3) x
dentro ou fora da equipe. A matriz esta em
documentation/decisoes/matriz-de-acesso.md; este arquivo cobre cada celula.

- censurado (versao com tarja): todo membro da equipe;
- parcial: todo membro; cobre so os dados acima do nivel do cargo (cada nivel
  tem a sua versao em cache); quem tem o nivel minimo recebe o original;
- original: so a partir de SAFEMASK_NIVEL_MIN_DESCENSURA (padrao 3, lider);
- fora da equipe, na mesma organizacao ou em outra: 404 em tudo, nunca 403.
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#87).
"""

import pytest

from app.core import autorizacao
from app.core.security import criar_token_jwt
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from tests.conftest import CONTEUDO_CENSURADO

ORIGINAL = b"%PDF-1.4\noriginal-sem-tarja\n%%EOF\n"
PARCIAL = b"%PDF-1.4\nparcial\n%%EOF\n"


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _pessoa(seed, nome, cargo=None):
    db = seed["db"]
    pessoa = Usuario(
        nome=nome,
        email=f"matriz-{nome.lower()}@safemask.example.com",
        senha_hash="x",
        organizacao_id=seed["organizacao"].organizacao_id,
    )
    db.add(pessoa)
    db.flush()
    if cargo is not None:
        db.add(UsuarioEquipe(user_id=pessoa.user_id, team_id=seed["equipe_a"].team_id, cargo_id=cargo.cargo_id))
    db.commit()
    return pessoa


@pytest.fixture
def cenario(client, seed, documento, dados_sensiveis, tmp_path, scanner_registrado, monkeypatch):
    """Documento da Equipe A, enviado pela lider, com dados de nivel 2 e 3."""
    monkeypatch.delenv(autorizacao.VARIAVEL_NIVEL_MIN_DESCENSURA, raising=False)
    scanner = scanner_registrado([])
    db = seed["db"]
    doc = documento(seed["user_team_a"], hash_documento="hmatriz",
                    caminho_storage="uploads/censurados/hmatriz_tarjado.pdf")
    db.add(doc)
    db.flush()
    db.add_all([
        dados_sensiveis(doc.doc_id, nivel_requerido=2),
        dados_sensiveis(doc.doc_id, nivel_requerido=3),
    ])
    db.commit()
    (tmp_path / "originais" / "hmatriz.pdf").write_bytes(ORIGINAL)
    (tmp_path / "censurados" / "hmatriz_tarjado.pdf").write_bytes(CONTEUDO_CENSURADO)

    pessoas = {
        "lider": seed["usuario"],
        "supervisor": _pessoa(seed, "Sueli", seed["cargo_supervisor"]),
        "membro": _pessoa(seed, "Mauro", seed["cargo_membro"]),
        "fora_da_equipe": _pessoa(seed, "Fabio"),
        "outra_organizacao": seed["usuario_globex"],
    }
    return {"client": client, "doc": doc, "pessoas": pessoas, "scanner": scanner, "tmp": tmp_path}


def _get(cenario, quem, rota):
    doc_id = cenario["doc"].doc_id
    return cenario["client"].get(rota.format(id=doc_id), headers=_auth(cenario["pessoas"][quem]))


DE_FORA = ["fora_da_equipe", "outra_organizacao"]
DA_EQUIPE = ["membro", "supervisor", "lider"]


# --- versao censurada ---------------------------------------------------------


@pytest.mark.parametrize("quem", DA_EQUIPE)
def test_censurado_liberado_para_todo_membro_da_equipe(cenario, quem):
    resp = _get(cenario, quem, "/documentos/censurados/{id}/arquivo")

    assert resp.status_code == 200, resp.text
    assert resp.content == CONTEUDO_CENSURADO


@pytest.mark.parametrize("quem", DE_FORA)
@pytest.mark.parametrize("rota", [
    "/documentos/censurados/{id}",
    "/documentos/censurados/{id}/arquivo",
    "/documentos/{id}/parcial",
    "/documentos/{id}/original",
])
def test_quem_esta_fora_recebe_404_em_todas_as_versoes(cenario, quem, rota):
    assert _get(cenario, quem, rota).status_code == 404


# --- parcial --------------------------------------------------------------------


@pytest.mark.parametrize(("quem", "cobertos"), [("membro", 2), ("supervisor", 1)])
def test_parcial_cobre_so_o_que_esta_acima_do_nivel_do_cargo(cenario, quem, cobertos):
    resp = _get(cenario, quem, "/documentos/{id}/parcial")

    assert resp.status_code == 200, resp.text
    assert resp.content == PARCIAL
    caixas = sum(len(v) for v in cenario["scanner"].itens_para_cobrir.values())
    assert caixas == cobertos


def test_cada_nivel_tem_a_sua_parcial_em_cache(cenario):
    _get(cenario, "membro", "/documentos/{id}/parcial")
    _get(cenario, "supervisor", "/documentos/{id}/parcial")
    _get(cenario, "membro", "/documentos/{id}/parcial")

    cache = sorted(p.name for p in (cenario["tmp"] / "censurados").glob("hmatriz_parcial_*"))
    assert [n.split("_")[2] for n in cache] == ["nivel1", "nivel2"]
    assert cenario["scanner"].chamadas_parcial == 2


def test_lider_recebe_o_original_pela_rota_parcial(cenario):
    resp = _get(cenario, "lider", "/documentos/{id}/parcial")

    assert resp.status_code == 200
    assert resp.content == ORIGINAL


# --- original -------------------------------------------------------------------


def test_lider_recebe_o_original(cenario):
    resp = _get(cenario, "lider", "/documentos/{id}/original")

    assert resp.status_code == 200
    assert resp.content == ORIGINAL


@pytest.mark.parametrize("quem", ["membro", "supervisor"])
def test_abaixo_do_nivel_minimo_o_original_e_recusado(cenario, quem):
    assert _get(cenario, quem, "/documentos/{id}/original").status_code == 403


@pytest.mark.parametrize(("quem", "pode"), [("membro", False), ("supervisor", False), ("lider", True)])
def test_detalhe_informa_quem_pode_ver_o_original(cenario, quem, pode):
    corpo = _get(cenario, quem, "/documentos/censurados/{id}").json()

    assert corpo["pode_descensurar"] is pode
    assert corpo["pode_descensura_parcial"] is True


# --- nivel minimo configuravel --------------------------------------------------


@pytest.mark.parametrize(("nivel_min", "quem", "esperado"), [
    ("2", "supervisor", 200),
    ("2", "membro", 403),
    ("1", "membro", 200),
])
def test_nivel_minimo_configuravel(cenario, monkeypatch, nivel_min, quem, esperado):
    monkeypatch.setenv(autorizacao.VARIAVEL_NIVEL_MIN_DESCENSURA, nivel_min)

    assert _get(cenario, quem, "/documentos/{id}/original").status_code == esperado
    corpo = _get(cenario, quem, "/documentos/censurados/{id}").json()
    assert corpo["pode_descensurar"] is (esperado == 200)


@pytest.mark.parametrize("valor", ["", "abc", "0", "9"])
def test_valor_ausente_ou_invalido_volta_ao_lider(monkeypatch, valor):
    monkeypatch.setenv(autorizacao.VARIAVEL_NIVEL_MIN_DESCENSURA, valor)

    assert autorizacao.nivel_min_descensura() == autorizacao.NIVEL_LIDER


# --- listagem da equipe ---------------------------------------------------------


@pytest.mark.parametrize("quem", DA_EQUIPE)
def test_listagem_da_equipe_mostra_os_documentos_de_todos(cenario, quem, seed):
    resp = cenario["client"].get(
        f"/documentos/listar/{seed['equipe_a'].team_id}", headers=_auth(cenario["pessoas"][quem])
    )

    assert resp.status_code == 200, resp.text
    assert [d["doc_id"] for d in resp.json()["documentos"]] == [cenario["doc"].doc_id]


@pytest.mark.parametrize("quem", DE_FORA)
def test_listagem_da_equipe_responde_404_para_quem_esta_fora(cenario, quem, seed):
    resp = cenario["client"].get(
        f"/documentos/listar/{seed['equipe_a'].team_id}", headers=_auth(cenario["pessoas"][quem])
    )

    assert resp.status_code == 404
