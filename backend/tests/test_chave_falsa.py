"""A "chave criptografica" falsa saiu da API e das telas.

`documentos.chave_criptografica` e um SHA-256 de metadados: nenhum caminho
do codigo cifra com ele, mas as telas Documentos Censurados e Descensura o
mostravam como "Chave criptografica". A coluna continua no banco (NOT NULL),
so deixa de ser exposta.
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#146).
"""

from pathlib import Path

from app.core.security import criar_token_jwt

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def _auth(usuario):
    token = criar_token_jwt({"sub": usuario.email, "nome": usuario.nome})
    return {"Authorization": f"Bearer {token}"}


def test_detalhe_nao_expoe_a_chave_falsa(client, seed, documento):
    db = seed["db"]
    doc = documento(seed["user_team_a"])
    db.add(doc)
    db.commit()

    resp = client.get(f"/documentos/censurados/{doc.doc_id}", headers=_auth(seed["usuario"]))

    assert resp.status_code == 200, resp.text
    assert "chave_criptografica" not in resp.json()


def test_telas_nao_mostram_chave_criptografica():
    telas = [
        FRONTEND / "js" / "documentos" / "censurados.js",
        FRONTEND / "js" / "documentos" / "descensura.js",
        FRONTEND / "html" / "documentos" / "censurados.html",
        FRONTEND / "html" / "documentos" / "descensura.html",
    ]
    for tela in telas:
        texto = tela.read_text(encoding="utf-8")
        assert "documento.chave_criptografica" not in texto, tela.name
        assert "Chave criptografica" not in texto, tela.name
