"""Consulta da trilha de auditoria.

Supervisor ou lider (cargo.nivel >= 2) ve os eventos das proprias equipes, da
propria organizacao. Membro comum e quem esta fora da equipe recebem 403, com
a mesma mensagem para tudo: respostas diferentes revelariam o que existe.
Eventos sem equipe (login, cadastro, redefinicao de senha) nao aparecem aqui.
Trazido do PI-III (CAMPUSCEUB/SafeMask#13).
"""

import csv
import io
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, aliased

from app.core.audit import ACOES
from app.core.autorizacao import NIVEL_SUPERVISOR, cargo_na_equipe, equipes_auditaveis
from app.core.current_user import get_current_user
from app.core.datas import iso_utc
from app.database import get_db
from app.models.cargo import Cargo
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.routes.documentos import buscar_documento_autorizado, equipe_do_documento

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])

NIVEL_MIN_AUDITORIA = NIVEL_SUPERVISOR

SEM_PERMISSAO = "Voce nao tem permissao para consultar este historico de auditoria."


def _em_utc(valor: datetime | None) -> datetime | None:
    """UTC sem fuso, o formato em que `data_hora` e gravada; sem fuso = UTC."""
    if valor is None or valor.tzinfo is None:
        return valor
    return valor.astimezone(UTC).replace(tzinfo=None)


def filtros_da_consulta(db: Session, usuario: Usuario, team_id, doc_id, acao, data_inicio, data_fim) -> list:
    """Confere a permissao e devolve os filtros da consulta."""
    permitidas = equipes_auditaveis(db, usuario)
    if not permitidas:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SEM_PERMISSAO)

    if team_id is not None and team_id not in permitidas:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SEM_PERMISSAO)

    if doc_id is not None:
        # O cargo que conta e o da equipe dona do documento.
        documento = buscar_documento_autorizado(db, usuario, doc_id)
        equipe = equipe_do_documento(db, documento) if documento else None
        cargo = cargo_na_equipe(db, usuario, equipe.team_id) if equipe else None
        if not cargo or cargo["nivel"] < NIVEL_MIN_AUDITORIA:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SEM_PERMISSAO)

    if acao is not None and acao not in ACOES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Acao desconhecida. Valores aceitos: {', '.join(sorted(ACOES))}.",
        )

    inicio, fim = _em_utc(data_inicio), _em_utc(data_fim)
    if inicio and fim and inicio > fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="data_inicio precisa ser anterior a data_fim.",
        )

    filtros = [LogAuditoria.team_id.in_(permitidas)]
    if team_id is not None:
        filtros.append(LogAuditoria.team_id == team_id)
    if doc_id is not None:
        filtros.append(LogAuditoria.doc_id == doc_id)
    if acao is not None:
        filtros.append(LogAuditoria.acao == acao)
    if inicio is not None:
        filtros.append(LogAuditoria.data_hora >= inicio)
    if fim is not None:
        filtros.append(LogAuditoria.data_hora <= fim)
    return filtros


def eventos_da_consulta(db: Session, filtros: list):
    """Eventos com os nomes de quem agiu, cargo, documento, equipe e alvo."""
    # Duas FKs para usuario (quem agiu e o alvo): cada uma com o seu alias.
    alvo = aliased(Usuario)
    return (
        db.query(LogAuditoria, Usuario.nome, Cargo.nome, Documento.nome_original, Equipe.nome, alvo.nome)
        .join(Usuario, Usuario.user_id == LogAuditoria.user_id)
        .outerjoin(Cargo, Cargo.cargo_id == LogAuditoria.cargo_id)
        .outerjoin(Documento, Documento.doc_id == LogAuditoria.doc_id)
        .outerjoin(Equipe, Equipe.team_id == LogAuditoria.team_id)
        .outerjoin(alvo, alvo.user_id == LogAuditoria.alvo_user_id)
        .filter(*filtros)
        # log_id desempata eventos gravados no mesmo segundo.
        .order_by(LogAuditoria.data_hora.desc(), LogAuditoria.log_id.desc())
    )


def _serializar(evento, usuario_nome, cargo_nome, documento_nome, equipe_nome, alvo_nome) -> dict:
    return {
        "log_id": evento.log_id,
        "data_hora": iso_utc(evento.data_hora),
        "acao": evento.acao,
        "resultado": evento.resultado,
        "usuario": {"user_id": evento.user_id, "nome": usuario_nome},
        "cargo": cargo_nome,
        "documento": {"doc_id": evento.doc_id, "nome": documento_nome} if evento.doc_id else None,
        "equipe": {"team_id": evento.team_id, "nome": equipe_nome},
        "alvo": {"user_id": evento.alvo_user_id, "nome": alvo_nome} if evento.alvo_user_id else None,
        "ip_origem": evento.ip_origem,
    }


FiltroEquipe = Annotated[int | None, Query(description="Somente eventos desta equipe")]
FiltroDocumento = Annotated[int | None, Query(description="Somente eventos deste documento")]
FiltroAcao = Annotated[str | None, Query(description="Somente esta acao, ex.: ver_original")]
FiltroInicio = Annotated[datetime | None, Query(description="Instante inicial, inclusive (ISO 8601; sem fuso = UTC)")]
FiltroFim = Annotated[datetime | None, Query(description="Instante final, inclusive (ISO 8601; sem fuso = UTC)")]


@router.get("", response_model=dict)
def consultar_historico(
    team_id: FiltroEquipe = None,
    doc_id: FiltroDocumento = None,
    acao: FiltroAcao = None,
    data_inicio: FiltroInicio = None,
    data_fim: FiltroFim = None,
    pagina: Annotated[int, Query(ge=1, description="Pagina desejada, a partir de 1")] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100, description="Eventos por pagina (maximo 100)")] = 20,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """Historico de auditoria das equipes que o usuario pode auditar, do mais recente ao mais antigo."""
    filtros = filtros_da_consulta(db, usuario_atual, team_id, doc_id, acao, data_inicio, data_fim)

    total = db.query(LogAuditoria).filter(*filtros).count()
    linhas = eventos_da_consulta(db, filtros).offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": (total + por_pagina - 1) // por_pagina,
        "eventos": [_serializar(*linha) for linha in linhas],
    }


# ------------------------------------------------------- exportacao em CSV

COLUNAS_CSV = [
    "ID do evento", "Data e hora (UTC)", "Ação", "Resultado", "Usuário",
    "Cargo", "Equipe", "Documento", "Alvo", "IP de origem",
]

# Texto que comeca com estes caracteres vira formula ao abrir na planilha
# (injecao de CSV). Nomes e titulos sao digitados por usuarios, entao saem
# com um apostrofo na frente, que a planilha mostra como texto.
_INICIO_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def _texto_seguro(valor) -> str:
    if valor is None:
        return ""
    texto = str(valor)
    return f"'{texto}" if texto.startswith(_INICIO_DE_FORMULA) else texto


@router.get("/exportar")
def exportar_historico(
    team_id: FiltroEquipe = None,
    doc_id: FiltroDocumento = None,
    acao: FiltroAcao = None,
    data_inicio: FiltroInicio = None,
    data_fim: FiltroFim = None,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """Historico em CSV, com os mesmos filtros e a mesma permissao da consulta.

    Todos os eventos do filtro, sem paginacao. UTF-8 com BOM e separador `;`,
    para abrir com acentos no Excel em portugues; data em UTC com fuso.
    """
    filtros = filtros_da_consulta(db, usuario_atual, team_id, doc_id, acao, data_inicio, data_fim)

    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(COLUNAS_CSV)
    for evento, usuario_nome, cargo_nome, documento_nome, equipe_nome, alvo_nome in eventos_da_consulta(db, filtros).all():
        escritor.writerow([
            evento.log_id,
            iso_utc(evento.data_hora) or "",
            evento.acao,
            evento.resultado,
            _texto_seguro(usuario_nome),
            cargo_nome or "",
            _texto_seguro(equipe_nome),
            _texto_seguro(documento_nome),
            _texto_seguro(alvo_nome),
            evento.ip_origem,
        ])

    nome = f"auditoria-safemask-{datetime.now(UTC):%Y-%m-%d}.csv"
    return Response(
        content=("\ufeff" + saida.getvalue()).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
