"""Comprovante de anonimizacao do documento (PI-III #217).

`GET /documentos/{id}/comprovante` gera, em memoria, um PDF com o que foi
feito no documento: tipos de dado tarjados e quantidade, paginas, ajustes da
revisao, quem enviou, equipe, data, hash e nivel de seguranca, sem nenhum
dado pessoal do documento. Qualquer membro da equipe baixa; quem esta fora
recebe 404. Gerar o comprovante vira evento de auditoria.
"""

import io
import json

import pdfplumber
import pytest

from app.core.security import criar_token_jwt
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from tests.conftest import gerar_pdf_texto

CPF = "529.982.247-25"
EMAIL = "titular@exemplo.com.br"
NOME = "Maria Ficticia Souza"


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _pessoa(seed, nome, cargo=None):
    db = seed["db"]
    pessoa = Usuario(nome=nome, email=f"comp-{nome.lower()}@safemask.example.com", senha_hash="x",
                     organizacao_id=seed["organizacao"].organizacao_id)
    db.add(pessoa)
    db.flush()
    if cargo is not None:
        db.add(UsuarioEquipe(user_id=pessoa.user_id, team_id=seed["equipe_a"].team_id, cargo_id=cargo.cargo_id))
    db.commit()
    return pessoa


@pytest.fixture
def cenario(client, seed):
    linhas = ["Contrato", f"Contratante: {NOME}", f"CPF {CPF}", f"E-mail {EMAIL}", f"Outro CPF {CPF}"]
    resposta = client.post(
        "/documentos/upload", headers=_auth(seed["usuario"]),
        files={"file": ("c.pdf", gerar_pdf_texto(linhas), "application/pdf")},
        data={"titulo": "Contrato de teste", "nivel_seguranca": "3", "teams": f"[{seed['equipe_a'].team_id}]",
              "trechos_extras": json.dumps([NOME])},
    )
    assert resposta.status_code == 201, resposta.text
    return {
        "client": client, "seed": seed, "doc_id": resposta.json()["doc_id"], "hash": resposta.json()["hash"],
        "membro": _pessoa(seed, "Mauro", seed["cargo_membro"]),
        "fora": _pessoa(seed, "Fabio"),
    }


def _comprovante(cenario, usuario):
    return cenario["client"].get(f"/documentos/{cenario['doc_id']}/comprovante", headers=_auth(usuario))


def _texto(resposta) -> str:
    with pdfplumber.open(io.BytesIO(resposta.content)) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def test_membro_baixa_o_comprovante_em_pdf(cenario):
    resposta = _comprovante(cenario, cenario["membro"])
    assert resposta.status_code == 200, resposta.text
    assert resposta.headers["content-type"].startswith("application/pdf")
    assert resposta.content.startswith(b"%PDF")
    assert "comprovante" in resposta.headers["content-disposition"]
    assert resposta.headers["x-content-type-options"] == "nosniff"


def test_comprovante_tem_o_que_foi_feito(cenario):
    texto = _texto(_comprovante(cenario, cenario["seed"]["usuario"]))
    assert "Comprovante de anonimização" in texto
    assert "Contrato de teste" in texto
    assert "Ana" in texto
    assert cenario["hash"] in texto.replace("\n", "")
    assert "Proteção alta" in texto
    assert "CPF: 2 tarja(s)" in texto
    assert "E-mail: 1 tarja(s)" in texto
    assert "Trecho marcado na revisão: 1 tarja(s)" in texto
    assert "acrescentados=1" in texto
    assert "cifrado" not in texto  # no grupo o original nao e cifrado


def test_comprovante_nao_tem_dado_pessoal_do_documento(cenario):
    texto = _texto(_comprovante(cenario, cenario["seed"]["usuario"]))
    for dado in (CPF, "529.982", EMAIL, "titular", NOME, "Ficticia"):
        assert dado not in texto


def test_fora_da_equipe_recebe_404_e_fica_na_trilha(cenario):
    assert _comprovante(cenario, cenario["fora"]).status_code == 404
    negados = cenario["seed"]["db"].query(LogAuditoria).filter_by(
        user_id=cenario["fora"].user_id, acao="gerar_comprovante", resultado="negado",
    ).count()
    assert negados == 1


def test_outra_organizacao_recebe_404(cenario):
    assert _comprovante(cenario, cenario["seed"]["usuario_globex"]).status_code == 404


def test_gerar_vira_evento_de_auditoria(cenario):
    _comprovante(cenario, cenario["membro"])
    eventos = cenario["seed"]["db"].query(LogAuditoria).filter_by(
        user_id=cenario["membro"].user_id, doc_id=cenario["doc_id"], acao="gerar_comprovante",
    ).all()
    assert [e.resultado for e in eventos] == ["sucesso"]
