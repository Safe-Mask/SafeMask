"""Entrega dinamica por nivel: o coracao do modo servidor do SafeMask.

O mesmo documento pedido por cargos diferentes recebe versoes diferentes, e a
versao parcial tem cache por (documento, nivel, caixas a cobrir) — regenerar
um PDF rasterizado a cada pedido custa alto. Cada entrega fica na auditoria
com o detalhe do que foi servido.
"""

import pytest

from app.core.security import criar_token_jwt
from app.models.log_auditoria import LogAuditoria
from tests.conftest import CONTEUDO_CENSURADO

PDF_PADRAO = b"%PDF-1.4\nconteudo\n%%EOF\n"


def _auth(usuario):
    token = criar_token_jwt({"sub": usuario.email, "nome": usuario.nome})
    return {"Authorization": f"Bearer {token}"}


def _parcial(client, seed, doc_id):
    return client.get(
        f"/documentos/{doc_id}/parcial",
        headers=_auth(seed["usuario"]),
    )


def _eventos(db, doc_id, acao=None):
    db.expire_all()
    consulta = db.query(LogAuditoria).filter(LogAuditoria.doc_id == doc_id)
    if acao:
        consulta = consulta.filter(LogAuditoria.acao == acao)
    return consulta.order_by(LogAuditoria.log_id).all()


def _distribuir_cargo(db, seed, cargo):
    """Ana muda de cargo na Equipe B (membro -> supervisor/lider)."""
    from app.models.usuario_equipe import UsuarioEquipe

    vinculo_b = (
        db.query(UsuarioEquipe)
        .filter_by(user_id=seed["usuario"].user_id, team_id=seed["equipe_b"].team_id)
        .first()
    )
    vinculo_b.cargo_id = cargo.cargo_id
    db.commit()


@pytest.fixture
def doc_nivel_supervisor(client, seed, scanner_registrado):
    """Documento na Equipe B (Ana e membro la) com um item que exige nivel 2.

    O nivel de um item e o que a politica da equipe dona decide (o scan
    aplica `niveis.get(tipo)`): a fixture grava a politica da Equipe B em
    CPF=2 antes do upload para o item realmente valer nivel 2.
    """
    from app.models.politica_nivel import PoliticaNivel

    db = seed["db"]
    db.add(PoliticaNivel(team_id=seed["equipe_b"].team_id, tipo_entidade="CPF", nivel_requerido=2))
    db.commit()

    scanner = scanner_registrado([(2, 0)])
    upload = client.post(
        "/documentos/upload",
        data={"titulo": "ata", "nivel_seguranca": "3",
              "teams": f'[{seed["equipe_b"].team_id}]'},
        files={"file": ("ata.pdf", PDF_PADRAO, "application/pdf")},
        headers=_auth(seed["usuario"]),
    )
    assert upload.status_code in (200, 201), upload.text
    return scanner, upload.json()["doc_id"]


def test_membro_recebe_parcial_e_segunda_busca_usa_cache(
    client, seed, doc_nivel_supervisor
):
    """Membro (nivel 1) pega a versao tarjada; repetir o pedido nao regera."""
    import pathlib

    scanner, doc_id = doc_nivel_supervisor
    db = seed["db"]

    primeira = _parcial(client, seed, doc_id)
    assert primeira.status_code == 200, primeira.text
    assert primeira.content.startswith(b"%PDF")
    assert scanner.chamadas_parcial == 1

    segunda = _parcial(client, seed, doc_id)
    assert segunda.status_code == 200
    assert segunda.content == primeira.content
    assert scanner.chamadas_parcial == 1  # cache, nao regeracao

    detalhes = [e.detalhe for e in _eventos(db, doc_id, acao="ver_parcial")]
    assert "parcial_nivel1" in detalhes
    assert "parcial_nivel1_cache" in detalhes


def test_supervisor_recebe_a_censurada_fixa(client, seed, doc_nivel_supervisor):
    """Supervisor (nivel 2): nada a cobrir, recebe a versao integralmente tarjada."""
    db = seed["db"]
    scanner, doc_id = doc_nivel_supervisor

    _distribuir_cargo(db, seed, seed["cargo_supervisor"])
    resposta = _parcial(client, seed, doc_id)

    assert resposta.status_code == 200
    assert resposta.content == CONTEUDO_CENSURADO
    detalhes = [e.detalhe for e in _eventos(db, doc_id, acao="ver_parcial")]
    assert detalhes[-1] == "parcial_nivel2"


def test_lider_recebe_o_original_integral(client, seed, doc_nivel_supervisor):
    """Lider (nivel >= descensura): recebe o original, com detalhe na trilha."""
    db = seed["db"]
    _, doc_id = doc_nivel_supervisor

    _distribuir_cargo(db, seed, seed["cargo_lider"])
    resposta = _parcial(client, seed, doc_id)

    assert resposta.status_code == 200
    assert resposta.content == PDF_PADRAO
    detalhes = [e.detalhe for e in _eventos(db, doc_id, acao="ver_original")]
    assert detalhes[-1] == "original_integral"


def test_mudanca_nos_itens_invalida_o_cache(client, seed, doc_nivel_supervisor):
    """Item novo muda a assinatura das caixas; a nova versao e regerada."""
    from app.models.dado_sensivel import DadoSensivel

    db = seed["db"]
    scanner, doc_id = doc_nivel_supervisor

    assert _parcial(client, seed, doc_id).status_code == 200
    assert scanner.chamadas_parcial == 1

    db.add(
        DadoSensivel(
            doc_id=doc_id,
            tipo_entidade="CPF",
            conteudo_hash="novo-item",
            pagina=0,
            coordenadas=[50, 50, 120, 70],
            espaco_coordenadas="pdf",
            nivel_requerido=3,
        )
    )
    db.commit()

    resposta = _parcial(client, seed, doc_id)
    assert resposta.status_code == 200
    # Item a mais -> chave diferente -> geracao nova (cache nao vaza).
    assert scanner.chamadas_parcial == 2
