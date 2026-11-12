"""Painel de conformidade no dashboard (PI-III #228).

`GET /dashboard/conformidade` devolve, so das equipes do usuario:
- tarjas por tipo de dado;
- documentos e tarjas por mes (ultimos N meses, padrao 6);
- acessos negados nos ultimos 30 dias, por acao, so das equipes em que o
  usuario pode consultar a auditoria (supervisor ou lider).
"""

import itertools
from datetime import datetime, timedelta

import pytest

from app.core.security import criar_token_jwt
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe

_SEQ = itertools.count(1)


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _documento(db, user_team_id, tipos, criado_em=None):
    marca = next(_SEQ)
    doc = Documento(
        user_team_id=user_team_id, nome_original=f"Doc {marca}", extensao="pdf", tamanho_bytes=10,
        nivel_seguranca=1, chave_criptografica="x", hash_documento=f"{marca:064d}",
        caminho_storage="censurados/x.pdf", status_processamento="CONCLUIDO",
        criado_em=criado_em or datetime.utcnow(),
    )
    db.add(doc)
    db.flush()
    for tipo in tipos:
        db.add(DadoSensivel(doc_id=doc.doc_id, tipo_entidade=tipo, conteudo_hash="h", pagina=0,
                            coordenadas=[0, 0, 1, 1], nivel_requerido=1))
    db.flush()


def _negado(db, user_id, team_id, acao="ver_original", quando=None):
    db.add(LogAuditoria(user_id=user_id, team_id=team_id, acao=acao, resultado="negado",
                        ip_origem="-", data_hora=quando or datetime.utcnow()))
    db.flush()


@pytest.fixture
def cenario(seed):
    """Ana: lider na Equipe A e membro na B. Equipe C, da mesma organizacao, sem a Ana."""
    db = seed["db"]
    org = seed["organizacao"].organizacao_id
    outro = Usuario(nome="Outro", email="painel-outro@safemask.example.com", senha_hash="x", organizacao_id=org)
    equipe_c = Equipe(nome="Equipe C", descricao="C", organizacao_id=org)
    db.add_all([outro, equipe_c])
    db.flush()
    vinculo_c = UsuarioEquipe(user_id=outro.user_id, team_id=equipe_c.team_id, cargo_id=seed["cargo_lider"].cargo_id)
    db.add(vinculo_c)
    db.flush()

    _documento(db, seed["user_team_a"], ["CPF", "CPF", "EMAIL"])
    _documento(db, seed["user_team_b"], ["CPF", "ENDERECO"])
    _documento(db, vinculo_c.user_team_id, ["CPF", "CPF", "CPF", "CNH"])  # equipe sem a Ana
    _documento(db, seed["user_team_a"], ["RG"], criado_em=datetime.utcnow() - timedelta(days=400))

    _negado(db, outro.user_id, seed["equipe_a"].team_id, "ver_original")
    _negado(db, outro.user_id, seed["equipe_a"].team_id, "ver_parcial")
    _negado(db, outro.user_id, seed["equipe_b"].team_id)  # na B a Ana e membro
    _negado(db, outro.user_id, equipe_c.team_id)  # equipe sem a Ana
    _negado(db, outro.user_id, seed["equipe_a"].team_id, quando=datetime.utcnow() - timedelta(days=40))
    db.commit()
    return seed


def _painel(client, usuario, meses=None):
    rota = "/dashboard/conformidade" + (f"?meses={meses}" if meses is not None else "")
    resposta = client.get(rota, headers=_auth(usuario))
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_tarjas_por_tipo_so_das_minhas_equipes(client, cenario):
    tipos = {t["tipo"]: t["quantidade"] for t in _painel(client, cenario["usuario"])["tarjas_por_tipo"]}
    assert tipos == {"CPF": 3, "EMAIL": 1, "ENDERECO": 1, "RG": 1}


def test_tarjas_por_tipo_vem_com_rotulo_e_em_ordem(client, cenario):
    lista = _painel(client, cenario["usuario"])["tarjas_por_tipo"]
    assert lista[0] == {"tipo": "CPF", "rotulo": "CPF", "quantidade": 3}
    assert [t["quantidade"] for t in lista] == sorted((t["quantidade"] for t in lista), reverse=True)


def test_por_mes_tem_os_ultimos_meses_com_zeros(client, cenario):
    meses = _painel(client, cenario["usuario"])["por_mes"]
    assert len(meses) == 6
    assert meses[-1] == {"mes": datetime.utcnow().strftime("%Y-%m"), "documentos": 2, "tarjas": 5}
    assert sum(m["tarjas"] for m in meses) == 5  # o documento de 400 dias atras nao entra


def test_negados_so_onde_posso_ver_a_auditoria(client, cenario):
    negados = _painel(client, cenario["usuario"])["negados"]
    assert negados["visivel"] is True and negados["dias"] == 30 and negados["total"] == 2
    assert {n["acao"]: n["quantidade"] for n in negados["por_acao"]} == {"ver_original": 1, "ver_parcial": 1}


def test_membro_comum_nao_ve_negados(client, seed):
    db = seed["db"]
    membro = Usuario(nome="M", email="painel-m@safemask.example.com", senha_hash="x",
                     organizacao_id=seed["organizacao"].organizacao_id)
    db.add(membro)
    db.flush()
    db.add(UsuarioEquipe(user_id=membro.user_id, team_id=seed["equipe_a"].team_id, cargo_id=seed["cargo_membro"].cargo_id))
    db.commit()
    _negado(db, membro.user_id, seed["equipe_a"].team_id)
    db.commit()
    assert _painel(client, membro)["negados"] == {"visivel": False, "dias": 30, "total": 0, "por_acao": []}


def test_outra_organizacao_nao_ve_nada_da_acme(client, cenario):
    painel = _painel(client, cenario["usuario_globex"])
    assert painel["tarjas_por_tipo"] == []
    assert painel["negados"]["total"] == 0


@pytest.mark.parametrize("meses, esperado", [(1, 1), (12, 12), (0, 1), (99, 24)])
def test_numero_de_meses_tem_limites(client, cenario, meses, esperado):
    assert len(_painel(client, cenario["usuario"], meses)["por_mes"]) == esperado


def test_exige_login(client):
    assert client.get("/dashboard/conformidade").status_code == 401
