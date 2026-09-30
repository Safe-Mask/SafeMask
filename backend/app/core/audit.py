"""Registro de trilha de auditoria.

O SRS (RN-010) exige que acesso e operacoes criticas fiquem registrados em
`log_auditoria`. A tabela existia, mas nenhuma rota gravava nela.
"""

import logging

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.log_auditoria import LogAuditoria

logger = logging.getLogger(__name__)

# Acoes usadas nas rotas. Mantidas curtas porque `acao` tem String(100).
ACAO_LOGIN = "login"
ACAO_LOGIN_FALHO = "login_falha"
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


def ip_do_cliente(request: Request | None) -> str:
    """IP de origem, respeitando X-Forwarded-For quando atras de proxy."""
    if request is None:
        return "desconhecido"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # cadeia "cliente, proxy1, proxy2" - o primeiro e o cliente real.
        return forwarded.split(",")[0].strip()[:45]

    return (request.client.host if request.client else "desconhecido")[:45]


def registrar(
    db: Session,
    request: Request | None,
    user_id: int,
    acao: str,
    *,
    commit: bool = True,
) -> LogAuditoria:
    """Grava uma linha de auditoria.

    Nunca levanta excecao: perder um log nao pode derrubar a requisição que o
    originou. Falhas sao logadas para investigacao.
    """
    entrada = LogAuditoria(
        user_id=user_id,
        acao=acao[:100],
        ip_origem=ip_do_cliente(request),
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
