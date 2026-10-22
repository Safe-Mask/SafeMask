"""Datas da API com fuso explicito.

As datas saiam sem fuso (`2026-10-20T18:21:28`) e o navegador as lia como
hora local: em Brasilia, 3 horas adiantadas. Correcao trazida do PI-III
(CAMPUSCEUB/SafeMask#112).
"""

from datetime import datetime, timedelta, timezone

from app.core.datas import iso_utc
from app.core.security import criar_token_jwt


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def test_data_sem_fuso_e_tratada_como_utc():
    assert iso_utc(datetime(2026, 10, 20, 18, 21, 28)) == "2026-10-20T18:21:28+00:00"


def test_data_com_outro_fuso_e_convertida_para_utc():
    brasilia = timezone(timedelta(hours=-3))
    assert iso_utc(datetime(2026, 10, 20, 15, 21, 28, tzinfo=brasilia)) == "2026-10-20T18:21:28+00:00"


def test_data_ausente_continua_ausente():
    assert iso_utc(None) is None


def test_rotas_devolvem_datas_com_fuso(client, seed, documento):
    db = seed["db"]
    doc = documento(seed["user_team_a"], criado_em=datetime(2026, 10, 20, 18, 21, 28))
    db.add(doc)
    seed["equipe_a"].criado_em = datetime(2026, 10, 1, 12, 0, 0)
    db.commit()
    auth = _auth(seed["usuario"])

    detalhe = client.get(f"/equipes/{seed['equipe_a'].team_id}", headers=auth).json()
    censurados = client.get("/documentos/censurados", headers=auth).json()
    item = client.get(f"/documentos/censurados/{doc.doc_id}", headers=auth).json()

    assert detalhe["criado_em"].endswith("+00:00")
    assert detalhe["documentos_lista"][0]["criado_em"] == "2026-10-20T18:21:28+00:00"
    assert all(m["criado_em"] is None or m["criado_em"].endswith("+00:00") for m in detalhe["membros_lista"])
    assert censurados["documentos"][0]["criado_em"] == "2026-10-20T18:21:28+00:00"
    assert item["criado_em"] == "2026-10-20T18:21:28+00:00"
