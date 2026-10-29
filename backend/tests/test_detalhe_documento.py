"""Detalhes do documento trazem o nome da equipe, como a listagem.

A tela Documentos Censurados preenche o campo Equipe com `equipe_nome`, o
mesmo campo da listagem. Os detalhes devolviam a equipe so em `equipe.nome`,
e a tela mostrava "-".
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#187).
"""

from app.core.security import criar_token_jwt


def _auth(usuario):
    token = criar_token_jwt({"sub": usuario.email, "nome": usuario.nome})
    return {"Authorization": f"Bearer {token}"}


def test_detalhe_traz_o_nome_da_equipe_como_na_listagem(client, seed, documento):
    db = seed["db"]
    doc = documento(seed["user_team_a"])
    db.add(doc)
    db.commit()

    detalhe = client.get(f"/documentos/censurados/{doc.doc_id}", headers=_auth(seed["usuario"]))
    lista = client.get("/documentos/censurados", headers=_auth(seed["usuario"]))

    assert detalhe.status_code == 200, detalhe.text
    na_lista = next(d for d in lista.json()["documentos"] if d["doc_id"] == doc.doc_id)
    assert detalhe.json()["equipe_nome"] == "Equipe A" == na_lista["equipe_nome"]
    assert detalhe.json()["equipe"]["nome"] == "Equipe A"
