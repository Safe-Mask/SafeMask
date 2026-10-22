"""Exportacao da trilha de auditoria em CSV (GET /auditoria/exportar).

Mesmos filtros e mesma permissao da consulta; UTF-8 com BOM e `;` para abrir
com acentos no Excel; nomes digitados por usuarios protegidos contra injecao
de formula. Trazido do PI-III (CAMPUSCEUB/SafeMask#14).
"""

import csv
import io
from datetime import datetime

from app.core.security import criar_token_jwt
from app.models.log_auditoria import LogAuditoria


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _evento(db, user_id, team_id, acao="ver_censurado", quando=datetime(2026, 10, 20, 12)):
    db.add(LogAuditoria(user_id=user_id, team_id=team_id, acao=acao, ip_origem="1.2.3.4", data_hora=quando))
    db.commit()


def _linhas(resp):
    texto = resp.content.decode("utf-8")
    assert texto.startswith("\ufeff")
    return list(csv.reader(io.StringIO(texto[1:]), delimiter=";"))


def test_exporta_os_eventos_com_cabecalho_e_nome_com_data(client, seed):
    db, ana = seed["db"], seed["usuario"]
    _evento(db, ana.user_id, seed["equipe_a"].team_id, acao="ver_original")
    _evento(db, ana.user_id, seed["equipe_a"].team_id, acao="upload_documento")

    resp = client.get("/auditoria/exportar", headers=_auth(ana))

    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert 'filename="auditoria-safemask-' in resp.headers["content-disposition"]
    linhas = _linhas(resp)
    assert linhas[0][:4] == ["ID do evento", "Data e hora (UTC)", "Ação", "Resultado"]
    assert len(linhas) == 3
    assert linhas[1][1] == "2026-10-20T12:00:00+00:00"


def test_aplica_os_mesmos_filtros_da_consulta(client, seed):
    db, ana = seed["db"], seed["usuario"]
    _evento(db, ana.user_id, seed["equipe_a"].team_id, acao="ver_original")
    _evento(db, ana.user_id, seed["equipe_a"].team_id, acao="upload_documento")

    linhas = _linhas(client.get("/auditoria/exportar?acao=upload_documento", headers=_auth(ana)))

    assert [linha[2] for linha in linhas[1:]] == ["upload_documento"]


def test_mesma_permissao_da_consulta(client, seed):
    resp = client.get(f"/auditoria/exportar?team_id={seed['equipe_b'].team_id}", headers=_auth(seed["usuario"]))
    assert resp.status_code == 403


def test_nome_que_parece_formula_sai_como_texto(client, seed):
    db, ana = seed["db"], seed["usuario"]
    ana.nome = "=HYPERLINK(\"http://x\")"
    db.commit()
    _evento(db, ana.user_id, seed["equipe_a"].team_id)

    linhas = _linhas(client.get("/auditoria/exportar", headers=_auth(ana)))

    assert linhas[1][4].startswith("'=")


def test_navegador_consegue_ler_o_nome_do_arquivo(client, seed):
    """Download por fetch so le Content-Disposition se o CORS expuser o header."""
    resp = client.get(
        "/auditoria/exportar",
        headers={**_auth(seed["usuario"]), "Origin": "http://localhost:5500"},
    )

    assert "content-disposition" in resp.headers.get("access-control-expose-headers", "").lower()
