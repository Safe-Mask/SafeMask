"""Politica de niveis por equipe.

O lider define o nivel exigido de cada tipo de dado; o scan aplica a politica
da equipe dona. Trazido do PI-III (CAMPUSCEUB/SafeMask#118).
"""

from app.core.security import criar_token_jwt
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from app.models.log_auditoria import LogAuditoria
from app.models.politica_nivel import PoliticaNivel
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from tests.conftest import CONTEUDO_PDF


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _politica(client, usuario, team_id):
    return client.get(f"/equipes/{team_id}/politica-niveis", headers=_auth(usuario))


def _definir(client, usuario, team_id, niveis):
    return client.put(f"/equipes/{team_id}/politica-niveis", headers=_auth(usuario), json={"niveis": niveis})


def test_membro_consulta_e_so_o_lider_pode_editar(client, seed):
    ana = seed["usuario"]
    da_a = _politica(client, ana, seed["equipe_a"].team_id).json()
    da_b = _politica(client, ana, seed["equipe_b"].team_id).json()

    assert da_a["pode_editar"] is True
    assert da_b["pode_editar"] is False
    telefone = next(t for t in da_a["tipos"] if t["tipo"] == "TELEFONE")
    assert telefone == {"tipo": "TELEFONE", "rotulo": "Telefone", "nivel": 2, "padrao": 2}


def test_lider_ajusta_e_volta_ao_padrao(client, seed):
    ana, team = seed["usuario"], seed["equipe_a"].team_id

    resp = _definir(client, ana, team, {"telefone": 3})
    assert resp.status_code == 200, resp.text
    assert next(t for t in resp.json()["politica"]["tipos"] if t["tipo"] == "TELEFONE")["nivel"] == 3
    assert seed["db"].query(PoliticaNivel).filter_by(team_id=team).count() == 1
    assert seed["db"].query(LogAuditoria).filter_by(acao="alterar_politica_niveis", resultado="sucesso").count() == 1

    _definir(client, ana, team, {"TELEFONE": 2})
    assert seed["db"].query(PoliticaNivel).filter_by(team_id=team).count() == 0


def test_tipo_ou_nivel_invalido_responde_400(client, seed):
    team = seed["equipe_a"].team_id
    assert _definir(client, seed["usuario"], team, {"PASSAPORTE": 2}).status_code == 400
    assert _definir(client, seed["usuario"], team, {"CPF": 4}).status_code == 400
    assert _definir(client, seed["usuario"], team, {}).status_code == 400


def test_membro_nao_altera_e_a_recusa_entra_na_trilha(client, seed):
    resp = _definir(client, seed["usuario"], seed["equipe_b"].team_id, {"CPF": 1})
    assert resp.status_code == 403
    assert seed["db"].query(LogAuditoria).filter_by(acao="alterar_politica_niveis", resultado="negado").count() == 1


def test_outra_organizacao_recebe_404(client, seed):
    assert _politica(client, seed["usuario_globex"], seed["equipe_a"].team_id).status_code == 404
    assert _definir(client, seed["usuario_globex"], seed["equipe_a"].team_id, {"CPF": 1}).status_code == 404


def test_upload_aplica_a_politica_da_equipe_dona(client, seed, scanner_registrado):
    _definir(client, seed["usuario"], seed["equipe_a"].team_id, {"CPF": 2})
    scanner_registrado([(3, 1)])

    resp = client.post(
        "/documentos/upload", headers=_auth(seed["usuario"]),
        files={"file": ("contrato.pdf", CONTEUDO_PDF, "application/pdf")},
        data={"titulo": "Contrato", "nivel_seguranca": "1",
              "teams": f"[{seed['equipe_a'].team_id}]"},
    )

    assert resp.status_code == 201, resp.text
    db = seed["db"]
    doc = db.query(Documento).filter_by(hash_documento=resp.json()["hash"]).one()
    itens = db.query(DadoSensivel).filter_by(doc_id=doc.doc_id).all()
    assert [i.nivel_requerido for i in itens] == [2]


def test_scanner_grava_o_nivel_da_politica(tmp_path, db_session, monkeypatch):
    from scanner.scanner import DocumentScanner, configuracoes_regex
    from tests.test_scan_salva_tarjas import _pdf_com_cpf

    origem = tmp_path / "doc.pdf"
    origem.write_bytes(_pdf_com_cpf())
    scanner = DocumentScanner.__new__(DocumentScanner)
    scanner.ia = None
    scanner.regex_config = configuracoes_regex()
    gravados = []
    original = scanner._salvar_dado

    def espiao(db, doc_id, page, page_num, texto, entity_type, level, *args, **kwargs):
        gravados.append((entity_type, level))
        return original(db, doc_id, page, page_num, texto, entity_type, level, *args, **kwargs)

    monkeypatch.setattr(scanner, "_salvar_dado", espiao)
    scanner.scan_and_save(str(origem), db_session, 1, "doc.pdf", 1, tmp_path / "o", tmp_path / "c", niveis={"CPF": 1})

    assert ("CPF", 1) in gravados
