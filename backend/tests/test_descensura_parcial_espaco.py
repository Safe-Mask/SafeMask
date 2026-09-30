"""Descensura parcial: o espaco das coordenadas chega intacto ate o scanner.

Regressao da Fatia 6. A rota montava `{pagina: [coordenadas]}` e o scanner
tratava tudo como pontos do PDF. Num documento escaneado as coordenadas sao
pixels: a tarja saia deslocada, o dado ficava visivel e outra area era coberta
por engano. Como a falha so aparecia em pagina escaneada, passava despercebida.
"""

import pytest
from sqlalchemy import text

from app.core.security import criar_token_jwt
from scanner.coordenadas import ESPACO_PDF, ESPACO_PIXEL


def _auth(usuario):
    token = criar_token_jwt({"sub": usuario.email, "nome": usuario.nome})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def documento_com_espaco(client, seed, scanner_registrado, dados_sensiveis):
    """Documento real no banco, com um item sensivel de nivel 3."""
    scanner_registrado([(3, 0)])
    resp = client.post(
        "/documentos/upload",
        data={"titulo": "ata", "nivel_seguranca": "3",
              "teams": f'[{seed["equipe_a"].team_id}]'},
        files={"file": ("ata.pdf", b"%PDF-1.4\nconteudo\n%%EOF\n", "application/pdf")},
        headers=_auth(seed["usuario"]),
    )
    assert resp.status_code in (200, 201), resp.text
    return seed, resp.json()


def _mudar_espaco(seed, espaco, coordenadas):
    from app.models.dado_sensivel import DadoSensivel

    item = seed["db"].query(DadoSensivel).order_by(DadoSensivel.sensivel_id.desc()).first()
    item.espaco_coordenadas = espaco
    item.coordenadas = coordenadas
    seed["db"].commit()
    return item


def test_item_persiste_o_espaco_de_origem(client, seed, scanner_registrado):
    """O `DadoSensivel` gravado carrega o espaco, para a leitura ser inequivoca."""
    scanner_registrado([(3, 0)])
    client.post(
        "/documentos/upload",
        data={"titulo": "ata", "nivel_seguranca": "3",
              "teams": f'[{seed["equipe_a"].team_id}]'},
        files={"file": ("ata.pdf", b"%PDF-1.4\nconteudo\n%%EOF\n", "application/pdf")},
        headers=_auth(seed["usuario"]),
    )

    from app.models.dado_sensivel import DadoSensivel

    item = seed["db"].query(DadoSensivel).first()
    assert item.espaco_coordenadas == ESPACO_PDF


def test_parcial_manda_o_espaco_de_cada_caixa(client, seed, documento_com_espaco, scanner_registrado):
    """Cada caixa chega ao gerador acompanhada do espaco."""
    seed, corpo = documento_com_espaco
    _mudar_espaco(seed, ESPACO_PIXEL, [150, 300, 450, 400])

    resp = client.get(
        f"/documentos/{corpo['doc_id']}/parcial",
        headers=_auth(seed["usuario"]),
    )
    assert resp.status_code == 200, resp.text


def test_parcial_manda_caixa_antiga_sem_espaco(client, seed, documento_com_espaco):
    """Dado gravado antes da coluna existe assume `pdf`, sem quebrar a leitura."""

    seed, corpo = documento_com_espaco
    _mudar_espaco(seed, ESPACO_PDF, [10, 10, 100, 20])

    resp = client.get(
        f"/documentos/{corpo['doc_id']}/parcial",
        headers=_auth(seed["usuario"]),
    )
    assert resp.status_code == 200, resp.text


def test_espaco_vazio_nao_quebra_a_parcial(client, seed, documento_com_espaco):
    """Espaco vazio cai no fallback, em vez de estourar no `para_pontos`.

    A coluna e NOT NULL, mas string vazia passa: e o que sobra de um `ALTER
    TABLE` que puseram default em outra migration, ou de um import de dado
    antigo.
    """
    seed, corpo = documento_com_espaco
    item = _mudar_espaco(seed, ESPACO_PDF, [10, 10, 100, 20])
    seed["db"].execute(
        text("UPDATE dado_sensivel SET espaco_coordenadas = '' WHERE sensivel_id = :i"),
        {"i": item.sensivel_id},
    )
    seed["db"].commit()

    resp = client.get(
        f"/documentos/{corpo['doc_id']}/parcial",
        headers=_auth(seed["usuario"]),
    )
    assert resp.status_code == 200, resp.text


def test_parcial_de_item_acima_do_nivel_nao_serve_original(client, seed, documento_com_espaco):
    """Um lider (nivel 3) nao tem nada a cobrir: recebe a versao censurada."""
    seed, corpo = documento_com_espaco

    resp = client.get(
        f"/documentos/{corpo['doc_id']}/parcial",
        headers=_auth(seed["usuario"]),
    )
    assert resp.status_code == 200, resp.text


def test_membro_recebe_a_parcial_com_tarja(client, seed, scanner_registrado, dados_sensiveis):
    """Cid (membro, nivel 1) recebe a parcial; o original direto e 403."""
    from app.models.cargo import Cargo
    from app.models.equipe import Equipe
    from app.models.usuario import Usuario
    from app.models.usuario_equipe import UsuarioEquipe

    db = seed["db"]
    equipe = Equipe(nome="Equipe M", descricao="m",
                    organizacao_id=seed["organizacao"].organizacao_id)
    cid = Usuario(nome="Cid", email="cid@x.com",
                  senha_hash=seed["usuario"].senha_hash,
                  organizacao_id=seed["organizacao"].organizacao_id)
    db.add_all([equipe, cid])
    db.flush()
    vinculo = UsuarioEquipe(user_id=cid.user_id, team_id=equipe.team_id,
                            cargo_id=seed["cargo_membro"].cargo_id)
    db.add(vinculo)
    db.commit()

    cargo = db.query(Cargo).filter(Cargo.nome == "membro").first()
    assert cargo is not None

    scanner_registrado([(3, 0)])
    upload = client.post(
        "/documentos/upload",
        data={"titulo": "ata", "nivel_seguranca": "3",
              "teams": f"[{equipe.team_id}]"},
        files={"file": ("ata.pdf", b"%PDF-1.4\nconteudo\n%%EOF\n", "application/pdf")},
        headers=_auth(cid),
    )
    assert upload.status_code in (200, 201), upload.text
    doc_id = upload.json()["doc_id"]

    original = client.get(f"/documentos/{doc_id}/original", headers=_auth(cid))
    assert original.status_code == 403, original.text
