from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.audit import RESULTADO_NEGADO
from app.core.autorizacao import equipes_auditaveis
from app.core.current_user import get_current_user
from app.core.datas import iso_utc
from app.database import get_db
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

NIVEIS_SEGURANCA = (1, 2, 3, 4)
SEM_PERMISSAO_METRICAS = (
    "Voce nao tem permissao para ver as metricas administrativas."
)


@router.get("/overview", response_model=dict)
def get_dashboard_overview(
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user)
    ):
    # Equipes do usuario e contagem de documentos por equipe.
    team_rows = (
        db.query(
            Equipe.team_id,
            Equipe.nome,
            func.count(Documento.doc_id).label("documentos")
        )
        .join(UsuarioEquipe, UsuarioEquipe.team_id == Equipe.team_id)
        .outerjoin(Documento, Documento.user_team_id == UsuarioEquipe.user_team_id)
        .filter(UsuarioEquipe.user_id == current_user.user_id)
        .group_by(Equipe.team_id, Equipe.nome)
        .order_by(desc("documentos"), Equipe.nome)
        .all()
    )

    team_ids = [
        row.team_id
        for row in (
            db.query(UsuarioEquipe.team_id)
            .filter(UsuarioEquipe.user_id == current_user.user_id)
            .distinct()
            .all()
        )
    ]

    total_docs = (
        db.query(func.count(Documento.doc_id))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(UsuarioEquipe.team_id.in_(team_ids))
        .scalar()
        or 0
    )

    docs_censurados = (
        db.query(func.count(Documento.doc_id))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(
            UsuarioEquipe.team_id.in_(team_ids),
            Documento.status_processamento == "CONCLUIDO",
        )
        .scalar()
        or 0
    )

    media_nivel = (
        db.query(func.avg(Documento.nivel_seguranca))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(UsuarioEquipe.team_id.in_(team_ids))
        .scalar()
    )

    docs_nivel_alto = (
        db.query(func.count(Documento.doc_id))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(
            UsuarioEquipe.team_id.in_(team_ids),
            Documento.nivel_seguranca >= 4
        )
        .scalar()
        or 0
    )

    recent_docs = (
        db.query(
            Documento.doc_id,
            Documento.nome_original,
            Documento.extensao,
            Documento.nivel_seguranca,
            Documento.criado_em,
            Equipe.nome.label("equipe_nome")
        )
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .join(Equipe, Equipe.team_id == UsuarioEquipe.team_id)
        .filter(UsuarioEquipe.team_id.in_(team_ids))
        .order_by(Documento.criado_em.desc())
        .limit(8)
        .all()
    )

    equipes = [
        {
            "team_id": row.team_id,
            "nome": row.nome,
            "documentos": int(row.documentos or 0)
        }
        for row in team_rows
    ]

    documentos_recentes = [
        {
            "doc_id": row.doc_id,
            "nome_original": row.nome_original,
            "extensao": row.extensao,
            "nivel_seguranca": row.nivel_seguranca,
            "equipe_nome": row.equipe_nome,
            "criado_em": iso_utc(row.criado_em)
        }
        for row in recent_docs
    ]

    return {
        "usuario": {
            "user_id": current_user.user_id,
            "nome": current_user.nome,
            "email": current_user.email
        },
        "metrics": {
            "total_equipes": len(equipes),
            "total_documentos": int(total_docs),
            "documentos_censurados": int(docs_censurados),
            "taxa_censura": round((docs_censurados / total_docs) * 100, 1) if total_docs else 0,
            "media_nivel_seguranca": round(float(media_nivel or 0), 2),
            "documentos_nivel_alto": int(docs_nivel_alto)
        },
        "equipes": equipes,
        "documentos_recentes": documentos_recentes
    }


@router.get("/metricas", response_model=dict)
def get_metricas_admin(
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user)
    ):
    """Metricas para o painel admin, limitadas as equipes que ele audita.

    Mesmo escopo da consulta de auditoria: supervisor/lider ve as proprias
    equipes; membro comum recebe 403. As contagens ignoram documento arquivado
    (`ativo=False`), que nao deve reaparecer em numero nenhum.
    """
    permitidas = equipes_auditaveis(db, current_user)
    if not permitidas:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=SEM_PERMISSAO_METRICAS,
        )

    por_nivel = {str(nivel): 0 for nivel in NIVEIS_SEGURANCA}
    linhas_nivel = (
        db.query(Documento.nivel_seguranca, func.count(Documento.doc_id))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(
            UsuarioEquipe.team_id.in_(permitidas),
            Documento.ativo.is_(True),
        )
        .group_by(Documento.nivel_seguranca)
        .all()
    )
    for nivel, quantidade in linhas_nivel:
        por_nivel[str(int(nivel))] = int(quantidade)

    por_status = {
        "AGUARDANDO": 0, "PROCESSANDO": 0, "CONCLUIDO": 0, "ERRO": 0,
    }
    linhas_status = (
        db.query(Documento.status_processamento, func.count(Documento.doc_id))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(
            UsuarioEquipe.team_id.in_(permitidas),
            Documento.ativo.is_(True),
        )
        .group_by(Documento.status_processamento)
        .all()
    )
    for situacao, quantidade in linhas_status:
        por_status[str(situacao)] = int(quantidade)

    linhas_negadas = (
        db.query(LogAuditoria.acao, func.count(LogAuditoria.log_id))
        .filter(
            LogAuditoria.team_id.in_(permitidas),
            LogAuditoria.resultado == RESULTADO_NEGADO,
        )
        .group_by(LogAuditoria.acao)
        .all()
    )
    por_acao = {acao: int(quantidade) for acao, quantidade in linhas_negadas}

    linhas_tipos = (
        db.query(
            DadoSensivel.tipo_entidade,
            func.count(DadoSensivel.sensivel_id).label("quantidade"),
        )
        .join(Documento, Documento.doc_id == DadoSensivel.doc_id)
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(
            UsuarioEquipe.team_id.in_(permitidas),
            Documento.ativo.is_(True),
        )
        .group_by(DadoSensivel.tipo_entidade)
        .order_by(desc("quantidade"), DadoSensivel.tipo_entidade)
        .limit(5)
        .all()
    )

    return {
        "escopo": {
            "equipes": [
                {"team_id": row.team_id, "nome": row.nome}
                for row in (
                    db.query(Equipe.team_id, Equipe.nome)
                    .filter(Equipe.team_id.in_(permitidas))
                    .order_by(Equipe.nome)
                    .all()
                )
            ],
        },
        "documentos": {
            "total": int(sum(por_nivel.values())),
            "por_nivel": por_nivel,
            "por_status": por_status,
        },
        "acessos_negados": {
            "total": int(sum(por_acao.values())),
            "por_acao": por_acao,
        },
        "top_tipos": [
            {"tipo": tipo, "quantidade": int(quantidade)}
            for tipo, quantidade in linhas_tipos
        ],
    }
