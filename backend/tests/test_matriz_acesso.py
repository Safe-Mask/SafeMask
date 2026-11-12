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
from app.models.log_auditoria import LogAuditoria
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


# --- nivel do documento (PI-III #176) ---------------------------------------
#
# O nivel de seguranca do documento vale no acesso (PI-III #176).
#
# O nivel escolhido no upload (1 Basico a 4 Protecao maxima) era so um rotulo.
# Agora entra junto com o cargo (documentation/decisoes/matriz-de-acesso.md):
#
# | Nivel do documento | Parcial a partir de | Original a partir de |
# | 1 Basico           | membro              | N                    |
# | 2 Protecao media   | supervisor          | maior entre N e 2    |
# | 3 Protecao alta    | supervisor          | lider                |
# | 4 Protecao maxima  | lider               | lider                |
#
# N = SAFEMASK_NIVEL_MIN_DESCENSURA (padrao 3). Abaixo do minimo, 403 e evento
# negado; quem esta fora continua recebendo 404.

NIVEL_DO_CARGO = {"membro": 1, "supervisor": 2, "lider": 3}
MIN_PARCIAL = {1: 1, 2: 2, 3: 2, 4: 3}


def _min_original(nivel_doc, minimo=3):
    return max(minimo, MIN_PARCIAL[nivel_doc], {1: 1, 2: 1, 3: 3, 4: 3}[nivel_doc])


def _classificar(cenario, seed, nivel_doc):
    cenario["doc"].nivel_seguranca = nivel_doc
    seed["db"].commit()


def _esperado(versao, quem, nivel_doc, minimo=3):
    nivel = NIVEL_DO_CARGO[quem]
    if nivel >= _min_original(nivel_doc, minimo):
        return ORIGINAL
    if versao == "parcial" and nivel >= MIN_PARCIAL[nivel_doc]:
        return PARCIAL
    return 403


def _negados(seed, quem_usuario):
    return seed["db"].query(LogAuditoria).filter_by(user_id=quem_usuario.user_id, resultado="negado").count()


@pytest.mark.parametrize("nivel_doc", [1, 2, 3, 4])
@pytest.mark.parametrize("quem", DA_EQUIPE)
@pytest.mark.parametrize("versao", ["parcial", "original"])
def test_nivel_do_documento(cenario, seed, monkeypatch, versao, quem, nivel_doc):
    monkeypatch.delenv(autorizacao.VARIAVEL_NIVEL_MIN_DESCENSURA, raising=False)
    _classificar(cenario, seed, nivel_doc)
    antes = _negados(seed, cenario["pessoas"][quem])

    resp = _get(cenario, quem, "/documentos/{id}/" + versao)
    esperado = _esperado(versao, quem, nivel_doc)

    if esperado == 403:
        assert resp.status_code == 403, resp.text
        assert _negados(seed, cenario["pessoas"][quem]) == antes + 1
    else:
        assert resp.status_code == 200, resp.text
        assert resp.content == esperado


@pytest.mark.parametrize("nivel_doc", [1, 2, 3, 4])
@pytest.mark.parametrize("quem", DE_FORA)
def test_fora_da_equipe_continua_404(cenario, seed, quem, nivel_doc):
    _classificar(cenario, seed, nivel_doc)
    for rota in ("/documentos/{id}/parcial", "/documentos/{id}/original"):
        assert _get(cenario, quem, rota).status_code == 404


@pytest.mark.parametrize("nivel_doc", [1, 2, 3, 4])
def test_detalhe_segue_o_nivel_do_documento(cenario, seed, monkeypatch, nivel_doc):
    monkeypatch.delenv(autorizacao.VARIAVEL_NIVEL_MIN_DESCENSURA, raising=False)
    _classificar(cenario, seed, nivel_doc)
    for quem in DA_EQUIPE:
        d = _get(cenario, quem, "/documentos/censurados/{id}").json()
        nivel = NIVEL_DO_CARGO[quem]
        assert d["pode_descensura_parcial"] is (nivel >= MIN_PARCIAL[nivel_doc])
        assert d["pode_descensurar"] is (nivel >= _min_original(nivel_doc))
        assert d["acesso_minimo"] == {"parcial": MIN_PARCIAL[nivel_doc], "original": _min_original(nivel_doc)}


@pytest.mark.parametrize("minimo", [1, 2])
@pytest.mark.parametrize("nivel_doc", [1, 2, 3, 4])
def test_original_nunca_exige_menos_que_a_parcial(cenario, seed, monkeypatch, minimo, nivel_doc):
    monkeypatch.setenv(autorizacao.VARIAVEL_NIVEL_MIN_DESCENSURA, str(minimo))
    _classificar(cenario, seed, nivel_doc)
    for quem in DA_EQUIPE:
        for versao in ("parcial", "original"):
            resp = _get(cenario, quem, "/documentos/{id}/" + versao)
            esperado = _esperado(versao, quem, nivel_doc, minimo)
            if esperado == 403:
                assert resp.status_code == 403, (quem, versao, resp.text)
            else:
                assert resp.status_code == 200 and resp.content == esperado, (quem, versao)


@pytest.mark.parametrize(("valor", "esperado"), [(None, 1), ("abc", 1), (0, 1), (7, 4), (2, 2)])
def test_nivel_invalido_ou_ausente(valor, esperado):
    assert autorizacao.nivel_min_parcial(valor) == MIN_PARCIAL[esperado]
