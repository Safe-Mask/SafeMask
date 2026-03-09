from fastapi import APIRouter, Depends
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.current_user import get_current_user
from app.database import get_db
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


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

    total_docs = (
        db.query(func.count(Documento.doc_id))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(UsuarioEquipe.user_id == current_user.user_id)
        .scalar()
        or 0
    )

    docs_censurados = (
        db.query(func.count(Documento.doc_id))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(
            UsuarioEquipe.user_id == current_user.user_id,
            Documento.chave_criptografica.isnot(None)
        )
        .scalar()
        or 0
    )

    media_nivel = (
        db.query(func.avg(Documento.nivel_seguranca))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(UsuarioEquipe.user_id == current_user.user_id)
        .scalar()
    )

    docs_nivel_alto = (
        db.query(func.count(Documento.doc_id))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(
            UsuarioEquipe.user_id == current_user.user_id,
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
        .filter(UsuarioEquipe.user_id == current_user.user_id)
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
            "criado_em": row.criado_em.isoformat() if row.criado_em else None
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
