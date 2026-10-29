"""Metricas do painel admin (Fase 3.2 do PLANO_DESKTOP)."""

from app.core.security import criar_token_jwt
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def _documento(seed, user_team_id, nivel=1, status="CONCLUIDO", ativo=True, hash_documento=None):
    documento = Documento(
        user_team_id=user_team_id,
        nome_original="relatorio.pdf",
        extensao="pdf",
        tamanho_bytes=10,
        nivel_seguranca=nivel,
        chave_criptografica="k",
        hash_documento=hash_documento or f"hash-{user_team_id}-{nivel}-{status}-{ativo}",
        caminho_storage="/tmp/relatorio.pdf",
        status_processamento=status,
        ativo=ativo,
    )
    seed["db"].add(documento)
    seed["db"].commit()
    seed["db"].refresh(documento)
    return documento


def _sensivel(seed, doc_id, tipo):
    dado = DadoSensivel(
        doc_id=doc_id,
        tipo_entidade=tipo,
        conteudo_hash="h",
        pagina=1,
        coordenadas=[10, 10, 20, 20],
        nivel_requerido=3,
    )
    seed["db"].add(dado)
    seed["db"].commit()
    return dado


def _negado(seed, usuario, team_id, acao):
    evento = LogAuditoria(
        user_id=usuario.user_id,
        team_id=team_id,
        acao=acao,
        ip_origem="1.2.3.4",
        resultado="negado",
    )
    seed["db"].add(evento)
    seed["db"].commit()
    return evento


def test_lider_ve_apenas_as_equipes_que_audita(client, seed):
    doc_a1 = _documento(seed, seed["user_team_a"], nivel=1)
    _documento(seed, seed["user_team_a"], nivel=3, status="ERRO")
    _documento(seed, seed["user_team_a"], nivel=2, status="CONCLUIDO", ativo=False)
    # Ana e membro da B, nao gestora: documento da B nao entra.
    _documento(seed, seed["user_team_b"], nivel=4)

    _sensivel(seed, doc_a1.doc_id, "CPF")
    _sensivel(seed, doc_a1.doc_id, "CPF")
    _sensivel(seed, doc_a1.doc_id, "EMAIL")
    _negado(seed, seed["usuario"], seed["equipe_a"].team_id, "ver_original")
    _negado(seed, seed["usuario"], seed["equipe_a"].team_id, "ver_parcial")
    _negado(seed, seed["usuario"], seed["equipe_b"].team_id, "ver_original")

    resposta = client.get("/dashboard/metricas", headers=_auth(seed["usuario"]))
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()

    assert [e["team_id"] for e in corpo["escopo"]["equipes"]] == [seed["equipe_a"].team_id]
    assert corpo["documentos"]["total"] == 2
    assert corpo["documentos"]["por_nivel"] == {"1": 1, "2": 0, "3": 1, "4": 0}
    assert corpo["documentos"]["por_status"]["CONCLUIDO"] == 1
    assert corpo["documentos"]["por_status"]["ERRO"] == 1
    assert corpo["acessos_negados"] == {
        "total": 2,
        "por_acao": {"ver_original": 1, "ver_parcial": 1},
    }
    assert corpo["top_tipos"] == [
        {"tipo": "CPF", "quantidade": 2},
        {"tipo": "EMAIL", "quantidade": 1},
    ]


def test_outro_lider_nao_ve_documentos_da_equipe_alheia(client, seed):
    _documento(seed, seed["user_team_a"], nivel=4)
    vinculo_globex = (
        seed["db"].query(UsuarioEquipe)
        .filter(
            UsuarioEquipe.user_id == seed["usuario_globex"].user_id,
            UsuarioEquipe.team_id == seed["equipe_globex"].team_id,
        )
        .one()
    )
    globex = _documento(seed, vinculo_globex.user_team_id, nivel=2)

    resposta = client.get(
        "/dashboard/metricas", headers=_auth(seed["usuario_globex"])
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()

    assert [e["team_id"] for e in corpo["escopo"]["equipes"]] == [
        seed["equipe_globex"].team_id
    ]
    assert corpo["documentos"]["total"] == 1
    assert corpo["documentos"]["por_nivel"]["2"] == 1
    assert corpo["documentos"]["por_nivel"]["4"] == 0
    assert globex.doc_id  # documento criado de fato


def test_membro_comum_nao_ve_metricas(client, seed):
    membro = Usuario(
        nome="Duda",
        email="duda@safemask.example.com",
        senha_hash="x",
        organizacao_id=seed["organizacao"].organizacao_id,
    )
    seed["db"].add(membro)
    seed["db"].flush()
    seed["db"].add(UsuarioEquipe(
        user_id=membro.user_id,
        team_id=seed["equipe_a"].team_id,
        cargo_id=seed["cargo_membro"].cargo_id,
    ))
    seed["db"].commit()

    resposta = client.get("/dashboard/metricas", headers=_auth(membro))
    assert resposta.status_code == 403
