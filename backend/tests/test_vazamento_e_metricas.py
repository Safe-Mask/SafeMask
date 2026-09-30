"""Regressoes de dados internos expostos e de metricas sem sentido.

Achados de auditoria fixados aqui:

1. `/documentos/censurados/{id}` devolvia `hash_documento` e `caminho_storage`.
   O hash e a chave de glob que localiza os arquivos no servidor, e o caminho
   entrega o layout do disco. Quem tem documento teu nao tem por que saber
   onde ele mora — e um hash de arquivo conteudo tambem serve para confirmar
   que voce ja tem uma copia do documento alheio.
2. `teams=[1, 1]` criava dois `Documento` apontando para o mesmo
   `user_team_id` e o mesmo arquivo.
3. `Documento.ativo` era o soft-delete previsto e nenhuma rota o lia: um
   documento arquivado continuava listado e servido.
4. A metrica `taxa_censura` do dashboard filtrava por
   `chave_criptografica IS NOT NULL`, coluna NOT NULL: o resultado era sempre
   "100% censurado", independente do que tivesse acontecido no processamento.
"""

import pytest
from sqlalchemy import text

from app.core.security import criar_token_jwt
from tests.conftest import CONTEUDO_CENSURADO, CONTEUDO_PDF, SENHA_SEED


@pytest.fixture
def documento(client, seed, scanner_registrado):
    scanner_registrado([(3, 0)])
    resp = client.post(
        "/documentos/upload",
        data={"titulo": "Contrato", "nivel_seguranca": "1",
              "teams": f"[{seed['equipe_a'].team_id}]"},
        files={"file": ("contrato.pdf", CONTEUDO_PDF, "application/pdf")},
        headers={"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"},
    )
    assert resp.status_code == 201, resp.text
    return seed, resp.json()["doc_id"]


def test_detalhe_nao_devolve_caminho_do_servidor(client, documento):
    seed, doc_id = documento
    resp = client.get(
        f"/documentos/censurados/{doc_id}",
        headers={"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"},
    )
    assert resp.status_code == 200, resp.text
    corpo = resp.json()

    assert "caminho_storage" not in corpo
    assert "hash_documento" not in corpo


def test_detalhe_nao_vaza_caminho_nem_em_texto(client, seed, documento):
    """O caminho do disco e o hash nao podem aparecer, nem escapados."""
    seed, doc_id = documento
    from app.models.documentos import Documento

    doc = seed["db"].query(Documento).filter(Documento.doc_id == doc_id).first()
    caminho, hash_arquivo = doc.caminho_storage, doc.hash_documento

    bruto = client.get(
        f"/documentos/censurados/{doc_id}",
        headers={"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"},
    ).text

    assert caminho not in bruto
    assert hash_arquivo not in bruto
    assert "uploads" not in bruto
    assert "tarjado.pdf" not in bruto


def test_detalhe_ainda_traz_o_que_a_tela_usa(client, documento):
    """O que o frontend mostra continua la: remover exposicao nao quebrou a tela."""
    seed, doc_id = documento
    corpo = client.get(
        f"/documentos/censurados/{doc_id}",
        headers={"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"},
    ).json()

    for campo in ("doc_id", "nome_original", "status_processamento",
                  "criado_em", "chave_criptografica", "preview_url", "equipe"):
        assert campo in corpo, campo


# --- teams duplicado ---------------------------------------------------------


def test_teams_duplicado_nao_cria_documento_duplo(client, seed, scanner_registrado):
    """`teams=[id, id]` criava duas linhas apontando para o mesmo arquivo."""
    scanner_registrado([(3, 0)])
    from app.models.documentos import Documento

    resp = client.post(
        "/documentos/upload",
        data={"titulo": "Contrato", "nivel_seguranca": "1",
              "teams": f"[{seed['equipe_a'].team_id}, {seed['equipe_a'].team_id}]"},
        files={"file": ("contrato.pdf", CONTEUDO_PDF, "application/pdf")},
        headers={"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"},
    )
    assert resp.status_code == 201, resp.text

    docs = seed["db"].query(Documento).all()
    assert len(docs) == 1, f"esperado 1 documento, vieram {len(docs)}"


def test_normalizar_team_ids_deduplica():
    from app.routes.documentos import normalizar_team_ids

    assert normalizar_team_ids("[3, 3, 1, 1, 2]") == [1, 2, 3]


# --- soft-delete -------------------------------------------------------------


def test_documento_arquivado_some_da_listagem(client, seed, documento):
    seed, doc_id = documento
    auth = {"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"}

    seed["db"].execute(
        text("UPDATE documentos SET ativo = 0 WHERE doc_id = :i"), {"i": doc_id}
    )
    seed["db"].commit()

    listagem = client.get(f"/documentos/listar/{seed['equipe_a'].team_id}", headers=auth)
    assert doc_id not in [d["doc_id"] for d in listagem.json()["documentos"]]


def test_documento_arquivado_nao_e_servido(client, seed, documento):
    seed, doc_id = documento
    auth = {"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"}

    seed["db"].execute(
        text("UPDATE documentos SET ativo = 0 WHERE doc_id = :i"), {"i": doc_id}
    )
    seed["db"].commit()

    assert client.get(f"/documentos/censurados/{doc_id}", headers=auth).status_code == 404
    assert client.get(f"/documentos/{doc_id}/parcial", headers=auth).status_code == 404
    assert client.get(f"/documentos/{doc_id}/original", headers=auth).status_code == 404


# --- metrica de censura ------------------------------------------------------


def test_taxa_de_censura_conta_processamento_real(client, seed, documento):
    """Documento em PROCESSANDO nao pode entrar como censurado."""
    seed, _ = documento
    auth = {"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"}

    seed["db"].execute(
        text("UPDATE documentos SET status_processamento = 'PROCESSANDO'")
    )
    seed["db"].commit()

    metricas = client.get("/dashboard/overview", headers=auth).json()["metrics"]
    assert metricas["total_documentos"] == 1
    assert metricas["documentos_censurados"] == 0
    assert metricas["taxa_censura"] == 0.0


def test_taxa_de_censura_100_quando_tudo_concluido(client, seed, documento):
    seed, _ = documento
    auth = {"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"}

    metricas = client.get("/dashboard/overview", headers=auth).json()["metrics"]
    assert metricas["documentos_censurados"] == metricas["total_documentos"] == 1
    assert metricas["taxa_censura"] == 100.0
