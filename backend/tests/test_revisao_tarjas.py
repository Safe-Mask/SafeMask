"""Revisao das tarjas antes de salvar (PI-III #208).

Antes, o upload detectava e ja gravava. Agora:
- `POST /documentos/analisar` devolve os achados MASCARADOS, sem gravar nada;
- o upload aceita `ignorar` (ids desmarcados) e `trechos_extras` (textos a
  cobrir) e aplica os ajustes na mesma deteccao;
- os ajustes entram na auditoria (`revisar_tarjas`) so como contagens.
"""

import itertools
import json

import pytest

from app.core.security import criar_token_jwt
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from app.models.log_auditoria import LogAuditoria
from tests.conftest import gerar_pdf_texto

_SEQ = itertools.count(1)
CPF = "529.982.247-25"
EMAIL = "titular@exemplo.com.br"
CNPJ = "11.222.333/0001-81"
NOME = "Maria Ficticia Souza"
LINHAS = ["Contrato de teste", f"Contratante: {NOME}", f"CPF {CPF}", f"E-mail {EMAIL}", f"CNPJ {CNPJ}"]


def _pdf():
    return gerar_pdf_texto(LINHAS + [f"ref {next(_SEQ)}"])


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _analisar(client, seed, conteudo):
    resposta = client.post(
        "/documentos/analisar", headers=_auth(seed["usuario"]),
        files={"file": ("contrato.pdf", conteudo, "application/pdf")},
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _enviar(client, seed, conteudo, ignorar=(), trechos=(), esperado=201):
    resposta = client.post(
        "/documentos/upload", headers=_auth(seed["usuario"]),
        files={"file": ("contrato.pdf", conteudo, "application/pdf")},
        data={
            "titulo": "Contrato", "nivel_seguranca": "1", "teams": f"[{seed['equipe_a'].team_id}]",
            "ignorar": json.dumps(list(ignorar)), "trechos_extras": json.dumps(list(trechos)),
        },
    )
    assert resposta.status_code == esperado, resposta.text
    return resposta.json()


def _tipos(db, doc_id):
    return sorted(d.tipo_entidade for d in db.query(DadoSensivel).filter_by(doc_id=doc_id))


def _eventos(db, doc_id, acao):
    return db.query(LogAuditoria).filter_by(doc_id=doc_id, acao=acao).all()


# ------------------------------------------------------------ mascara

@pytest.mark.parametrize("valor, tipo, esperado", [
    ("529.982.247-25", "CPF", "•••.•••.•••-25"),
    ("11.222.333/0001-81", "CNPJ", "••.•••.•••/••••-81"),
    ("titular@exemplo.com.br", "EMAIL", "•••••••@•••••••.•••.br"),
    ("4111 1111 1111 1111", "CARTAO", "•••• •••• •••• 1111"),
    ("61 99876-5432", "TELEFONE", "•• •••••-••32"),
    ("1234", "ENDERECO", "••••"),
])
def test_mascara(valor, tipo, esperado):
    from app.core.revisao import mascarar

    assert mascarar(valor, tipo) == esperado


# ------------------------------------------------------------ analise

def test_analise_devolve_achados_mascarados_e_nao_grava_nada(client, seed, tmp_path):
    db = seed["db"]
    antes = (db.query(Documento).count(), db.query(LogAuditoria).count())
    resposta = _analisar(client, seed, _pdf())

    assert sorted(a["tipo"] for a in resposta["achados"]) == ["CNPJ", "CPF", "EMAIL"]
    texto = json.dumps(resposta, ensure_ascii=False)
    for dado in (CPF, EMAIL, CNPJ, "529.982", "titular"):
        assert dado not in texto, f"dado inteiro na resposta: {dado}"
    assert all(a["id"] and a["pagina"] == 1 and a["ocorrencias"] == 1 for a in resposta["achados"])
    assert (db.query(Documento).count(), db.query(LogAuditoria).count()) == antes
    assert not any((tmp_path / "originais").iterdir()) and not any((tmp_path / "censurados").iterdir())


def test_analise_exige_login(client):
    resposta = client.post("/documentos/analisar", files={"file": ("c.pdf", _pdf(), "application/pdf")})
    assert resposta.status_code == 401


def test_analise_recusa_arquivo_que_nao_e_pdf(client, seed):
    resposta = client.post(
        "/documentos/analisar", headers=_auth(seed["usuario"]),
        files={"file": ("c.pdf", b"nao sou pdf", "application/pdf")},
    )
    assert resposta.status_code in (400, 415)


def test_ids_da_analise_sao_estaveis(client, seed):
    conteudo = _pdf()
    ids = [a["id"] for a in _analisar(client, seed, conteudo)["achados"]]
    assert ids == [a["id"] for a in _analisar(client, seed, conteudo)["achados"]]
    assert len(set(ids)) == len(ids)


# ------------------------------------------------------------ envio com ajustes

def test_desmarcar_um_achado_tira_a_tarja_dele(client, seed):
    conteudo = _pdf()
    cnpj = next(a["id"] for a in _analisar(client, seed, conteudo)["achados"] if a["tipo"] == "CNPJ")
    resposta = _enviar(client, seed, conteudo, ignorar=[cnpj])
    assert _tipos(seed["db"], resposta["doc_id"]) == ["CPF", "EMAIL"]
    assert resposta["desmarcados"] == 1


def test_trecho_acrescentado_e_tarjado_como_manual(client, seed):
    resposta = _enviar(client, seed, _pdf(), trechos=[NOME, "texto que nao existe"])
    db = seed["db"]
    assert _tipos(db, resposta["doc_id"]).count("MANUAL") == 1
    assert resposta["trechos_nao_encontrados"] == 1
    manual = db.query(DadoSensivel).filter_by(doc_id=resposta["doc_id"], tipo_entidade="MANUAL").one()
    assert manual.nivel_requerido == 3
    assert manual.coordenadas
    assert NOME not in (manual.conteudo_hash or "")


def test_sem_ajustes_o_envio_continua_igual(client, seed):
    resposta = _enviar(client, seed, _pdf())
    assert _tipos(seed["db"], resposta["doc_id"]) == ["CNPJ", "CPF", "EMAIL"]
    assert resposta["desmarcados"] == 0


# ------------------------------------------------------------ auditoria

def test_ajustes_vao_para_a_auditoria_so_como_contagens(client, seed):
    conteudo = _pdf()
    achados = _analisar(client, seed, conteudo)["achados"]
    ignorar = [a["id"] for a in achados if a["tipo"] in ("CNPJ", "EMAIL")]
    resposta = _enviar(client, seed, conteudo, ignorar=ignorar, trechos=[NOME, "nada disso aparece"])

    eventos = _eventos(seed["db"], resposta["doc_id"], "revisar_tarjas")
    assert len(eventos) == 1
    assert eventos[0].detalhe == "desmarcados=2; acrescentados=2; nao_encontrados=1"
    for dado in (NOME, CPF, EMAIL, CNPJ, "nada disso"):
        assert dado not in eventos[0].detalhe


def test_sem_ajustes_nao_ha_evento_de_revisao(client, seed):
    resposta = _enviar(client, seed, _pdf())
    assert _eventos(seed["db"], resposta["doc_id"], "revisar_tarjas") == []


def test_acao_nova_e_aceita_no_filtro_da_consulta():
    from app.core.audit import ACOES

    assert "revisar_tarjas" in ACOES


# ------------------------------------------------------------ limites

@pytest.mark.parametrize("campo, valor", [
    ("trechos", ["ab"]),
    ("trechos", ["x" * 121]),
    ("trechos", [f"trecho {i}" for i in range(21)]),
    ("trechos", [123]),
    ("ignorar", ["p0-CPF-1" * 10]),
])
def test_limites_da_revisao(client, seed, campo, valor):
    if campo == "trechos":
        _enviar(client, seed, _pdf(), trechos=valor, esperado=400)
    else:
        _enviar(client, seed, _pdf(), ignorar=valor, esperado=400)


def test_consulta_e_csv_mostram_o_detalhe(client, seed):
    from app.routes.auditoria import COLUNAS_CSV

    resposta = _enviar(client, seed, _pdf(), trechos=[NOME])
    consulta = client.get(f"/auditoria?doc_id={resposta['doc_id']}", headers=_auth(seed["usuario"]))
    assert consulta.status_code == 200, consulta.text
    eventos = consulta.json()["eventos"]
    revisao = [e for e in eventos if e["acao"] == "revisar_tarjas"]
    assert revisao and revisao[0]["detalhe"].startswith("desmarcados=0; acrescentados=1")
    assert COLUNAS_CSV[-1] == "Detalhe"
