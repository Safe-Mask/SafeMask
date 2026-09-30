"""Regressoes de seguranca do fluxo de documentos.

Bug de origem: ao compartilhar um PDF com varias equipes, `upload_documento`
cria um registro de `Documento` por equipe, mas o scanner so grava
`DadoSensivel` no primeiro. Um membro da segunda equipe abria
`/documentos/{doc_id}/parcial`, nao encontrava nenhum item e recebia o PDF
ORIGINAL sem censura.
"""

import pytest

from app.core.security import criar_token_jwt
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento

TOKEN = criar_token_jwt({"sub": "ana@safemask.local", "nome": "Ana"})
AUTH = {"Authorization": f"Bearer {TOKEN}"}

CONTEUDO_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
CONTEUDO_CENSURADO = b"%PDF-1.4\nconteudo-tarjado-pelo-scanner\n%%EOF\n"


class ScannerFalso:
    """Substitui o DocumentScanner para nao depender de torch/pdfplumber.

    Reproduz o contrato real: cria um `Documento`, cria `DadoSensivel` linked
    a esse unico doc_id e grava o PDF tarjado em `dir_censurado`.
    """

    def __init__(self, itens_sensiveis, doc_id_atribuido=None):
        self.itens_sensiveis = itens_sensiveis
        self.doc_id_atribuido = doc_id_atribuido
        self.chamadas = 0

    def scan_and_save(self, file_path, db, user_team_id, nome_original,
                      nivel_seguranca, dir_original, dir_censurado):
        from pathlib import Path

        self.chamadas += 1
        import hashlib

        conteudo = Path(file_path).read_bytes()
        hash_documento = hashlib.sha256(conteudo).hexdigest()

        doc = Documento(
            user_team_id=user_team_id,
            nome_original=nome_original,
            extensao="pdf",
            tamanho_bytes=len(conteudo),
            nivel_seguranca=nivel_seguranca,
            chave_criptografica="chave",
            hash_documento=hash_documento,
            caminho_storage=str(Path(dir_censurado) / f"{hash_documento}_tarjado.pdf"),
            status_processamento="CONCLUIDO",
            cpf_censurados=len(self.itens_sensiveis),
        )
        db.add(doc)
        db.flush()

        for nivel_requerido, pagina in self.itens_sensiveis:
            db.add(
                DadoSensivel(
                    doc_id=doc.doc_id,
                    tipo_entidade="CPF",
                    conteudo_hash="hash",
                    pagina=pagina,
                    coordenadas=[10, 10, 100, 20],
                    nivel_requerido=nivel_requerido,
                )
            )
        db.flush()

        Path(dir_censurado).mkdir(parents=True, exist_ok=True)
        Path(doc.caminho_storage).write_bytes(CONTEUDO_CENSURADO)

        return {
            "doc_id": doc.doc_id,
            "hash": hash_documento,
            "total_sensiveis": len(self.itens_sensiveis),
            "cpf_censurados": len(self.itens_sensiveis),
            "status": "CONCLUIDO",
        }

    def gerar_pdf_parcial(self, file_path, itens_para_cobrir, dir_destino, nome_saida):
        from pathlib import Path

        Path(dir_destino).mkdir(parents=True, exist_ok=True)
        destino = Path(dir_destino) / nome_saida
        destino.write_bytes(b"%PDF-1.4\nparcial\n%%EOF\n")
        return destino


@pytest.fixture
def scanner_registrado(monkeypatch):
    """Instala um ScannerFalso e devolve a fabrica."""

    def _instalar(itens_sensiveis):
        from app.routes import documentos as documentos_routes

        scanner = ScannerFalso(itens_sensiveis)
        monkeypatch.setattr(documentos_routes, "get_scanner", lambda: scanner)
        return scanner

    return _instalar


def _upload(client, teams, conteudo=CONTEUDO_PDF):
    return client.post(
        "/documentos/upload",
        headers=AUTH,
        files={"file": ("contrato.pdf", conteudo, "application/pdf")},
        data={"titulo": "Contrato", "nivel_seguranca": "1", "teams": teams},
    )


# --- Regressao 1: dados sensiveis precisam ser compartilhados --------------


def test_dados_sensiveis_sao_compartilhados_com_todas_as_equipes(
    client, seed, scanner_registrado, tmp_path
):
    """Todo Documento de um upload multi-equipe deve ter os mesmos itens."""
    db = seed["db"]
    scanner_registrado([(3, 1), (3, 1), (2, 2)])

    resp = _upload(client, f"[{seed['equipe_a'].team_id}, {seed['equipe_b'].team_id}]")
    assert resp.status_code == 201, resp.text

    docs = db.query(Documento).all()
    assert len(docs) == 2

    por_doc = {}
    for doc in docs:
        itens = db.query(DadoSensivel).filter(DadoSensivel.doc_id == doc.doc_id).all()
        por_doc[doc.doc_id] = sorted((i.tipo_entidade, i.nivel_requerido, i.pagina) for i in itens)

    assert por_doc[docs[0].doc_id] == [("CPF", 2, 2), ("CPF", 3, 1), ("CPF", 3, 1)]
    # Esta e a regressao: o segundo Documento nao pode ficar sem nenhum item,
    # senao /parcial responde com o PDF original.
    assert por_doc[docs[1].doc_id] == por_doc[docs[0].doc_id]


def test_parcial_nao_vaza_original_em_documento_compartilhado(
    client, seed, scanner_registrado, tmp_path
):
    """Membro da segunda equipe nunca recebe o PDF original."""
    db = seed["db"]
    scanner_registrado([(3, 1)])

    resp = _upload(client, f"[{seed['equipe_a'].team_id}, {seed['equipe_b'].team_id}]")
    assert resp.status_code == 201, resp.text

    docs = db.query(Documento).order_by(Documento.doc_id).all()
    doc_equipe_b = docs[1]
    assert doc_equipe_b.user_team_id == seed["user_team_b"]

    # Grava o original em disco como o upload faria.
    import hashlib

    hash_documento = hashlib.sha256(CONTEUDO_PDF).hexdigest()
    (tmp_path / "originais" / f"{hash_documento}.pdf").write_bytes(CONTEUDO_PDF)

    resp = client.get(f"/documentos/{doc_equipe_b.doc_id}/parcial", headers=AUTH)

    assert resp.status_code == 200, resp.text
    assert resp.content != CONTEUDO_PDF, "endpoint /parcial devolveu o PDF original sem censura"


# --- Regressao 2: documento sem itens nunca expoe o original --------------


def test_parcial_nao_expoe_original_quando_documento_nao_tem_itens(
    client, seed, scanner_registrado, tmp_path
):
    """Scan que nao encontrou nada nao pode autorizar o original.

    Usa a equipe B, onde Ana e `membro` (nivel 1): o cargo nao tem direito a
    descensura, entao qualquer original servido aqui e um vazamento.
    """
    db = seed["db"]
    scanner_registrado([])

    resp = _upload(client, f"[{seed['equipe_b'].team_id}]")
    assert resp.status_code == 201, resp.text

    import hashlib

    hash_documento = hashlib.sha256(CONTEUDO_PDF).hexdigest()
    (tmp_path / "originais" / f"{hash_documento}.pdf").write_bytes(CONTEUDO_PDF)

    doc = db.query(Documento).one()
    resp = client.get(f"/documentos/{doc.doc_id}/parcial", headers=AUTH)

    assert resp.status_code == 200, resp.text
    assert resp.content != CONTEUDO_PDF, "documento sem dados sensiveis devolveu o original"


def test_parcial_de_lider_ainda_recebe_o_original(client, seed, scanner_registrado, tmp_path):
    """Descensura de nivel 3+ continua entregando o original."""
    db = seed["db"]
    scanner_registrado([(3, 1)])

    resp = _upload(client, f"[{seed['equipe_a'].team_id}]")
    assert resp.status_code == 201, resp.text

    import hashlib

    hash_documento = hashlib.sha256(CONTEUDO_PDF).hexdigest()
    (tmp_path / "originais" / f"{hash_documento}.pdf").write_bytes(CONTEUDO_PDF)

    doc = db.query(Documento).one()
    resp = client.get(f"/documentos/{doc.doc_id}/parcial", headers=AUTH)

    assert resp.status_code == 200, resp.text
    assert resp.content == CONTEUDO_PDF
