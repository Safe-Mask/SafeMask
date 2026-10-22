"""Trilha de auditoria com contexto e tentativas negadas.

Cada evento de documento passa a dizer qual documento, de qual equipe, com que
cargo e com que resultado. A recusa por permissao vira evento "negado" quando
quem tentou e da mesma organizacao; de outra organizacao, nada e gravado (o
historico da empresa dona nao recebe nomes de outra). Trazido do PI-III
(CAMPUSCEUB/SafeMask#12).
"""

from sqlalchemy import create_engine, inspect, text

from app.core.security import criar_token_jwt
from app.models.documentos import Documento
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from tests.conftest import CONTEUDO_PDF


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _upload(client, seed, teams):
    resp = client.post(
        "/documentos/upload",
        headers=_auth(seed["usuario"]),
        files={"file": ("contrato.pdf", CONTEUDO_PDF, "application/pdf")},
        data={"titulo": "Contrato Sigiloso", "nivel_seguranca": "1", "teams": teams},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _eventos(db, **filtros):
    db.expire_all()
    return db.query(LogAuditoria).filter_by(**filtros).order_by(LogAuditoria.log_id).all()


def test_upload_gera_um_evento_por_equipe_com_documento_e_cargo(client, seed, scanner_registrado):
    scanner_registrado([(3, 1)])
    resposta = _upload(client, seed, f"[{seed['equipe_a'].team_id}, {seed['equipe_b'].team_id}]")

    eventos = _eventos(seed["db"], acao="upload_documento")
    docs = seed["db"].query(Documento).filter_by(hash_documento=resposta["hash"]).all()

    assert {(e.doc_id, e.team_id) for e in eventos} == {
        (d.doc_id, t) for d, t in zip(
            sorted(docs, key=lambda d: d.doc_id),
            [seed["equipe_a"].team_id, seed["equipe_b"].team_id],
            strict=True,
        )
    }
    cargos = {e.team_id: e.cargo_id for e in eventos}
    assert cargos[seed["equipe_a"].team_id] == seed["cargo_lider"].cargo_id
    assert cargos[seed["equipe_b"].team_id] == seed["cargo_membro"].cargo_id
    assert all(e.resultado == "sucesso" for e in eventos)


def test_cargo_insuficiente_para_o_original_gera_evento_negado(client, seed, scanner_registrado):
    # Ana e membro na Equipe B: o original exige lider.
    scanner_registrado([(3, 1)])
    resposta = _upload(client, seed, f"[{seed['equipe_b'].team_id}]")

    resp = client.get(f"/documentos/{resposta['doc_id']}/original", headers=_auth(seed["usuario"]))

    assert resp.status_code == 403
    negado = _eventos(seed["db"], acao="ver_original", resultado="negado")
    assert len(negado) == 1
    assert negado[0].doc_id == resposta["doc_id"]
    assert negado[0].cargo_id == seed["cargo_membro"].cargo_id


def test_pessoa_da_organizacao_fora_da_equipe_gera_evento_negado(client, seed, scanner_registrado):
    scanner_registrado([(3, 1)])
    resposta = _upload(client, seed, f"[{seed['equipe_a'].team_id}]")
    db = seed["db"]
    caio = Usuario(
        nome="Caio", email="caio@safemask.example.com", senha_hash="x",
        organizacao_id=seed["organizacao"].organizacao_id,
    )
    db.add(caio)
    db.flush()
    db.add(UsuarioEquipe(user_id=caio.user_id, team_id=seed["equipe_b"].team_id, cargo_id=seed["cargo_membro"].cargo_id))
    db.commit()

    resp = client.get(f"/documentos/censurados/{resposta['doc_id']}", headers=_auth(caio))

    assert resp.status_code == 404
    negado = _eventos(db, user_id=caio.user_id, resultado="negado")
    assert [(e.acao, e.doc_id, e.team_id, e.cargo_id) for e in negado] == [
        ("ver_censurado", resposta["doc_id"], seed["equipe_a"].team_id, None)
    ]


def test_outra_organizacao_nao_deixa_rastro_no_historico_da_dona(client, seed, scanner_registrado):
    scanner_registrado([(3, 1)])
    resposta = _upload(client, seed, f"[{seed['equipe_a'].team_id}]")

    resp = client.get(f"/documentos/{resposta['doc_id']}/parcial", headers=_auth(seed["usuario_globex"]))

    assert resp.status_code == 404
    assert _eventos(seed["db"], user_id=seed["usuario_globex"].user_id) == []


def test_evento_nao_guarda_titulo_nem_dado_pessoal(client, seed, scanner_registrado):
    scanner_registrado([(3, 1)])
    _upload(client, seed, f"[{seed['equipe_a'].team_id}]")

    for evento in _eventos(seed["db"]):
        valores = [str(getattr(evento, c.name)) for c in LogAuditoria.__table__.columns]
        assert not any("Sigiloso" in v or "@" in v for v in valores)


def test_banco_antigo_recebe_as_colunas_de_contexto(tmp_path):
    from app.database import garantir_schema_auditoria

    engine = create_engine(f"sqlite:///{(tmp_path / 'antigo.db').as_posix()}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE log_auditoria (log_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
            "acao VARCHAR(100) NOT NULL, ip_origem VARCHAR(45) NOT NULL, data_hora TIMESTAMP)"
        ))
        conn.execute(text("INSERT INTO log_auditoria (user_id, acao, ip_origem) VALUES (1, 'login', '1.2.3.4')"))

    garantir_schema_auditoria(engine)
    garantir_schema_auditoria(engine)  # segunda execucao nao falha

    colunas = {c["name"] for c in inspect(engine).get_columns("log_auditoria")}
    assert {"doc_id", "team_id", "cargo_id", "alvo_user_id", "resultado"} <= colunas
    with engine.connect() as conn:
        assert conn.execute(text("SELECT acao, resultado FROM log_auditoria")).one() == ("login", "sucesso")
