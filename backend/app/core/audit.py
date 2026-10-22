"""Registro de trilha de auditoria.

O SRS (RN-010) exige que acesso e operacoes criticas fiquem registrados em
`log_auditoria`. A tabela existia, mas nenhuma rota gravava nela.
"""

import logging

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.log_auditoria import LogAuditoria
from app.models.usuario_equipe import UsuarioEquipe

logger = logging.getLogger(__name__)

# Acoes usadas nas rotas. Mantidas curtas porque `acao` tem String(100).
ACAO_LOGIN = "login"
ACAO_LOGIN_FALHO = "login_falha"
ACAO_LOGIN_BLOQUEADO = "login_bloqueado"
ACAO_LOGOUT = "logout"
ACAO_CADASTRO = "cadastro"
ACAO_RESET_SENHA_SOLICITACAO = "reset_senha_solicitacao"
ACAO_RESET_SENHA = "reset_senha"
ACAO_UPLOAD = "upload_documento"
ACAO_UPLOAD_CENSURADO = "upload_documento_censurado"
ACAO_LISTAR_DOCUMENTOS = "listar_documentos"
ACAO_VER_ORIGINAL = "ver_original"
ACAO_VER_PARCIAL = "ver_parcial"
ACAO_VER_CENSURADO = "ver_censurado"
ACAO_CRIAR_EQUIPE = "criar_equipe"
ACAO_ATUALIZAR_EQUIPE = "atualizar_equipe"
ACAO_ADICIONAR_MEMBRO = "adicionar_membro"
ACAO_REMOVER_MEMBRO = "remover_membro"
ACAO_ALTERAR_CARGO = "alterar_cargo"
ACAO_ALTERAR_POLITICA_NIVEIS = "alterar_politica_niveis"

# Resultado: "negado" e a recusa por permissao (cargo insuficiente, ou pessoa
# da mesma organizacao fora da equipe dona do documento). Uma trilha que so
# registra sucesso nao serve para investigar incidente.
# Acoes aceitas no filtro da consulta (GET /auditoria).
ACOES = frozenset(
    valor for nome, valor in list(globals().items()) if nome.startswith("ACAO_") and isinstance(valor, str)
)

RESULTADO_SUCESSO = "sucesso"
RESULTADO_NEGADO = "negado"


def ip_do_cliente(request: Request | None) -> str:
    """IP de origem, respeitando X-Forwarded-For quando atras de proxy."""
    if request is None:
        return "desconhecido"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # cadeia "cliente, proxy1, proxy2" - o primeiro e o cliente real.
        return forwarded.split(",")[0].strip()[:45]

    return (request.client.host if request.client else "desconhecido")[:45]


def _equipe_do_documento(db: Session, documento) -> int | None:
    vinculo = (
        db.query(UsuarioEquipe)
        .filter(UsuarioEquipe.user_team_id == documento.user_team_id)
        .first()
    )
    return vinculo.team_id if vinculo else None


def _cargo_na_equipe(db: Session, user_id: int, team_id: int) -> int | None:
    """Cargo de quem agiu na equipe; None se a pessoa nao pertence a ela."""
    vinculo = (
        db.query(UsuarioEquipe)
        .filter(UsuarioEquipe.user_id == user_id, UsuarioEquipe.team_id == team_id)
        .first()
    )
    return vinculo.cargo_id if vinculo else None


def registrar(
    db: Session,
    request: Request | None,
    user_id: int,
    acao: str,
    *,
    commit: bool = True,
    documento=None,
    team_id: int | None = None,
    cargo_id: int | None = None,
    alvo_user_id: int | None = None,
    resultado: str = RESULTADO_SUCESSO,
) -> LogAuditoria:
    """Grava uma linha de auditoria.

    O contexto (documento, equipe, cargo de quem agiu, alvo e resultado) e o
    que permite responder "quem acessou este documento, com que cargo, e quem
    tentou sem permissao". Equipe e cargo sao deduzidos do documento quando
    nao informados. Nunca grava conteudo, titulo ou dado pessoal.

    Nunca levanta excecao: perder um log nao pode derrubar a requisição que o
    originou. Falhas sao logadas para investigacao.
    """
    try:
        if documento is not None and team_id is None:
            team_id = _equipe_do_documento(db, documento)
        if cargo_id is None and team_id is not None:
            cargo_id = _cargo_na_equipe(db, user_id, team_id)
    except Exception:
        logger.exception("Falha ao montar o contexto da auditoria: acao=%s", acao)

    entrada = LogAuditoria(
        user_id=user_id,
        acao=acao[:100],
        ip_origem=ip_do_cliente(request),
        doc_id=documento.doc_id if documento is not None else None,
        team_id=team_id,
        cargo_id=cargo_id,
        alvo_user_id=alvo_user_id,
        resultado=resultado,
    )
    try:
        db.add(entrada)
        if commit:
            db.commit()
        else:
            db.flush()
    except Exception:
        logger.exception("Falha ao registrar auditoria: acao=%s user=%s", acao, user_id)
        db.rollback()
    return entrada


def registrar_falha_login(db: Session, request: Request | None, user_id: int | None) -> None:
    """Tentativa de login sem usuario autenticavel usa user_id nulo ou -1.

    `log_auditoria.user_id` tem FK NOT NULL, entao tentativas anônimas entram
    com o menor id conhecido apenas para preservar o registro.
    """
    if user_id is None:
        return
    registrar(db, request, user_id, ACAO_LOGIN_FALHO)
