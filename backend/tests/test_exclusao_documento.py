"""Exclusao de documento e derivados, com confirmacao e auditoria.

Regra (art. 18, VI, da LGPD: eliminacao):

- so o lider da equipe dona do documento exclui; membro e supervisor
  recebem 403, quem esta fora da equipe recebe 404, e as recusas viram
  evento "negado" na trilha;
- a exclusao e fisica: somem o registro e os dados sensiveis dele;
- original, versao com tarja e parciais em cache sao compartilhados por hash
  entre copias e reenvios: so saem do disco quando nenhum outro documento
  usa aquele hash;
- documento ainda na fila do lote nao pode ser excluido (409);
- a trilha sobrevive: os eventos anteriores ficam sem o vinculo ao
  documento, e a exclusao gera o evento "excluir_documento".
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#23).
"""

from app.core.security import criar_token_jwt
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe

ACAO = "excluir_documento"


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _pessoa(seed, nome, equipe=None, cargo=None):
    db = seed["db"]
    pessoa = Usuario(
        nome=nome,
        email=f"{nome.lower()}@safemask.example.com",
        senha_hash="x",
        organizacao_id=seed["organizacao"].organizacao_id,
    )
    db.add(pessoa)
    db.flush()
    if equipe is not None:
        db.add(UsuarioEquipe(user_id=pessoa.user_id, team_id=equipe.team_id, cargo_id=cargo.cargo_id))
    db.commit()
    return pessoa


def _doc_com_arquivos(seed, documento, dados_sensiveis, tmp_path, user_team_id=None, hash_doc="h1", **kwargs):
    db = seed["db"]
    doc = documento(
        user_team_id or seed["user_team_a"],
        hash_documento=hash_doc,
        caminho_storage=f"uploads/censurados/{hash_doc}_tarjado.pdf",
        **kwargs,
    )
    db.add(doc)
    db.flush()
    db.add(dados_sensiveis(doc.doc_id, nivel_requerido=2))
    db.commit()
    (tmp_path / "originais" / f"{hash_doc}.pdf").write_bytes(b"original")
    (tmp_path / "censurados" / f"{hash_doc}_tarjado.pdf").write_bytes(b"tarjado")
    (tmp_path / "censurados" / f"{hash_doc}_parcial_nivel1_abc.pdf").write_bytes(b"parcial")
    return doc


def _arquivos(tmp_path, hash_doc="h1"):
    return sorted(
        p.name
        for pasta in ("originais", "censurados")
        for p in (tmp_path / pasta).glob(f"{hash_doc}*")
    )


def _eventos(db, **filtros):
    return db.query(LogAuditoria).filter_by(acao=ACAO, **filtros).all()


def test_lider_exclui_documento_dados_e_arquivos(client, seed, documento, dados_sensiveis, tmp_path):
    doc = _doc_com_arquivos(seed, documento, dados_sensiveis, tmp_path)
    doc_id = doc.doc_id

    resp = client.delete(f"/documentos/{doc_id}", headers=_auth(seed["usuario"]))

    assert resp.status_code == 200, resp.text
    assert resp.json()["arquivos_apagados"] == 3
    db = seed["db"]
    db.expire_all()
    assert db.get(Documento, doc_id) is None
    assert db.query(DadoSensivel).filter_by(doc_id=doc_id).count() == 0
    assert _arquivos(tmp_path) == []


def test_arquivos_compartilhados_ficam_ate_a_ultima_copia_sair(
    client, seed, documento, dados_sensiveis, tmp_path
):
    copia_a = _doc_com_arquivos(seed, documento, dados_sensiveis, tmp_path)
    db = seed["db"]
    copia_b = documento(seed["user_team_b"], hash_documento="h1")
    db.add(copia_b)
    db.commit()
    arquivos = _arquivos(tmp_path)

    resp = client.delete(f"/documentos/{copia_a.doc_id}", headers=_auth(seed["usuario"]))

    assert resp.status_code == 200, resp.text
    assert resp.json()["arquivos_apagados"] == 0
    assert _arquivos(tmp_path) == arquivos
    db.expire_all()
    assert db.get(Documento, copia_b.doc_id) is not None


def test_membro_recebe_403_e_a_recusa_fica_na_trilha(client, seed, documento, dados_sensiveis, tmp_path):
    # Ana e membro (nivel 1) da Equipe B.
    doc = _doc_com_arquivos(seed, documento, dados_sensiveis, tmp_path, user_team_id=seed["user_team_b"])

    resp = client.delete(f"/documentos/{doc.doc_id}", headers=_auth(seed["usuario"]))

    assert resp.status_code == 403
    db = seed["db"]
    db.expire_all()
    assert db.get(Documento, doc.doc_id) is not None
    assert len(_arquivos(tmp_path)) == 3
    negados = _eventos(db, user_id=seed["usuario"].user_id, resultado="negado")
    assert [e.doc_id for e in negados] == [doc.doc_id]


def test_supervisor_recebe_403(client, seed, documento, dados_sensiveis, tmp_path):
    supervisor = _pessoa(seed, "Sara", seed["equipe_a"], seed["cargo_supervisor"])
    doc = _doc_com_arquivos(seed, documento, dados_sensiveis, tmp_path)

    resp = client.delete(f"/documentos/{doc.doc_id}", headers=_auth(supervisor))

    assert resp.status_code == 403


def test_quem_e_da_organizacao_mas_esta_fora_da_equipe_recebe_404_e_fica_na_trilha(
    client, seed, documento, dados_sensiveis, tmp_path
):
    de_fora = _pessoa(seed, "Otto")
    doc = _doc_com_arquivos(seed, documento, dados_sensiveis, tmp_path)

    resp = client.delete(f"/documentos/{doc.doc_id}", headers=_auth(de_fora))

    assert resp.status_code == 404
    assert len(_eventos(seed["db"], user_id=de_fora.user_id, resultado="negado")) == 1
    assert len(_arquivos(tmp_path)) == 3


def test_outra_organizacao_recebe_404_sem_deixar_rastro(client, seed, documento, dados_sensiveis, tmp_path):
    doc = _doc_com_arquivos(seed, documento, dados_sensiveis, tmp_path)

    resp = client.delete(f"/documentos/{doc.doc_id}", headers=_auth(seed["usuario_globex"]))

    assert resp.status_code == 404
    assert _eventos(seed["db"], user_id=seed["usuario_globex"].user_id) == []


def test_documento_inexistente_responde_404(client, seed):
    resp = client.delete("/documentos/999999", headers=_auth(seed["usuario"]))

    assert resp.status_code == 404


def test_documento_ainda_na_fila_nao_e_excluido(client, seed, documento, dados_sensiveis, tmp_path):
    doc = _doc_com_arquivos(
        seed, documento, dados_sensiveis, tmp_path, status_processamento="PROCESSANDO"
    )

    resp = client.delete(f"/documentos/{doc.doc_id}", headers=_auth(seed["usuario"]))

    assert resp.status_code == 409
    assert len(_arquivos(tmp_path)) == 3


def test_trilha_sobrevive_a_exclusao(client, seed, documento, dados_sensiveis, tmp_path):
    doc = _doc_com_arquivos(seed, documento, dados_sensiveis, tmp_path)
    doc_id = doc.doc_id
    db = seed["db"]
    client.get(f"/documentos/censurados/{doc_id}", headers=_auth(seed["usuario"]))
    anterior = db.query(LogAuditoria).filter_by(doc_id=doc_id).first()
    assert anterior is not None

    client.delete(f"/documentos/{doc_id}", headers=_auth(seed["usuario"]))
    db.expire_all()

    assert db.get(LogAuditoria, anterior.log_id).doc_id is None
    exclusao = _eventos(db, user_id=seed["usuario"].user_id, resultado="sucesso")
    assert [e.team_id for e in exclusao] == [seed["equipe_a"].team_id]


def test_detalhe_informa_quem_pode_excluir(client, seed, documento, dados_sensiveis, tmp_path):
    doc_lider = _doc_com_arquivos(seed, documento, dados_sensiveis, tmp_path)
    doc_membro = _doc_com_arquivos(
        seed, documento, dados_sensiveis, tmp_path, user_team_id=seed["user_team_b"], hash_doc="h2"
    )

    def pode(doc):
        resp = client.get(f"/documentos/censurados/{doc.doc_id}", headers=_auth(seed["usuario"]))
        return resp.json()["pode_excluir"]

    assert pode(doc_lider) is True
    assert pode(doc_membro) is False
