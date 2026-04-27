from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.core.current_user import get_current_user
from app.database import get_db
from app.models.cargo import Cargo
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from app.schemas.equipe import EquipeCreate

router = APIRouter(prefix="/equipes", tags=["Equipes"])


def _current_team_ids(db: Session, user_id: int) -> List[int]:
    return [
        row.team_id
        for row in (
            db.query(UsuarioEquipe.team_id)
            .filter(UsuarioEquipe.user_id == user_id)
            .distinct()
            .all()
        )
    ]


def _get_cargo_by_name(db: Session, nomes: List[str]) -> Cargo | None:
    cargos = (
        db.query(Cargo)
        .filter(Cargo.nome.in_(nomes))
        .order_by(Cargo.nivel.asc())
        .all()
    )
    return cargos[0] if cargos else None


def _get_cargo_lider(db: Session) -> Cargo:
    cargo = db.query(Cargo).filter(Cargo.nome == "lider").first()
    if not cargo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cargo 'lider' não encontrado.",
        )
    return cargo


def _get_cargo_membro(db: Session) -> Cargo:
    cargo = _get_cargo_by_name(db, ["membro", "integrante", "colaborador"])
    if cargo:
        return cargo

    cargo = (
        db.query(Cargo)
        .filter(Cargo.nome != "lider")
        .order_by(Cargo.nivel.asc())
        .first()
    )
    return cargo or _get_cargo_lider(db)


def _serialize_member(member_row) -> dict:
    return {
        "user_team_id": member_row.user_team_id,
        "user_id": member_row.user_id,
        "nome": member_row.nome,
        "email": member_row.email,
        "cargo_nome": member_row.cargo_nome,
        "cargo_nivel": int(member_row.cargo_nivel or 0),
        "criado_em": member_row.criado_em.isoformat() if member_row.criado_em else None,
    }


def _load_team_detail(db: Session, current_user: Usuario, team_id: int):
    team_row = (
        db.query(
            Equipe.team_id,
            Equipe.nome,
            Equipe.descricao,
            Equipe.criado_em,
        )
        .join(UsuarioEquipe, UsuarioEquipe.team_id == Equipe.team_id)
        .filter(
            Equipe.team_id == team_id,
            UsuarioEquipe.user_id == current_user.user_id,
        )
        .first()
    )

    if not team_row:
        return None

    members = (
        db.query(
            UsuarioEquipe.user_team_id,
            Usuario.user_id,
            Usuario.nome,
            Usuario.email,
            Cargo.nome.label("cargo_nome"),
            Cargo.nivel.label("cargo_nivel"),
            UsuarioEquipe.criado_em,
        )
        .join(Usuario, Usuario.user_id == UsuarioEquipe.user_id)
        .join(Cargo, Cargo.cargo_id == UsuarioEquipe.cargo_id)
        .filter(UsuarioEquipe.team_id == team_id)
        .order_by(Cargo.nivel.desc(), Usuario.nome)
        .all()
    )

    documentos = (
        db.query(func.count(func.distinct(Documento.doc_id)))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(UsuarioEquipe.team_id == team_id)
        .scalar()
        or 0
    )

    return {
        "team_id": team_row.team_id,
        "nome": team_row.nome,
        "descricao": team_row.descricao,
        "criado_em": team_row.criado_em.isoformat() if team_row.criado_em else None,
        "membros": len(members),
        "documentos": int(documentos),
        "membros_lista": [_serialize_member(member) for member in members],
    }


@router.get("/overview", response_model=dict)
def get_equipes_overview(
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user)
    ):
    team_rows = (
        db.query(
            Equipe.team_id,
            Equipe.nome,
            Equipe.descricao,
            Equipe.criado_em,
            func.count(func.distinct(UsuarioEquipe.user_team_id)).label("membros"),
            func.count(func.distinct(Documento.doc_id)).label("documentos"),
        )
        .join(UsuarioEquipe, UsuarioEquipe.team_id == Equipe.team_id)
        .outerjoin(Documento, Documento.user_team_id == UsuarioEquipe.user_team_id)
        .filter(UsuarioEquipe.user_id == current_user.user_id)
        .group_by(Equipe.team_id, Equipe.nome, Equipe.descricao, Equipe.criado_em)
        .order_by(desc("membros"), Equipe.nome)
        .all()
    )

    equipes = []
    unique_member_ids = set()

    for row in team_rows:
        membros_rows = (
            db.query(
                UsuarioEquipe.user_team_id,
                Usuario.user_id,
                Usuario.nome,
                Usuario.email,
                Cargo.nome.label("cargo_nome"),
                Cargo.nivel.label("cargo_nivel"),
                UsuarioEquipe.criado_em,
            )
            .join(Usuario, Usuario.user_id == UsuarioEquipe.user_id)
            .join(Cargo, Cargo.cargo_id == UsuarioEquipe.cargo_id)
            .filter(UsuarioEquipe.team_id == row.team_id)
            .order_by(Cargo.nivel.desc(), Usuario.nome)
            .all()
        )

        membros = []
        for membro in membros_rows:
            unique_member_ids.add(membro.user_id)
            membros.append(_serialize_member(membro))

        cargo_usuario = next(
            (membro["cargo_nome"] for membro in membros if membro["user_id"] == current_user.user_id),
            None,
        )

        equipes.append({
            "team_id": row.team_id,
            "nome": row.nome,
            "descricao": row.descricao,
            "criado_em": row.criado_em.isoformat() if row.criado_em else None,
            "membros": int(row.membros or 0),
            "documentos": int(row.documentos or 0),
            "cargo_usuario": cargo_usuario,
            "membros_lista": membros,
        })

    equipe_mais_populosa = max(equipes, key=lambda item: item["membros"], default=None)
    media_membros = round(sum(item["membros"] for item in equipes) / len(equipes), 1) if equipes else 0

    return {
        "usuario": {
            "user_id": current_user.user_id,
            "nome": current_user.nome,
            "email": current_user.email,
        },
        "metrics": {
            "total_equipes": len(equipes),
            "total_membros": len(unique_member_ids),
            "total_documentos": int(sum(item["documentos"] for item in equipes)),
            "media_membros_por_equipe": media_membros,
            "equipe_maior_nome": equipe_mais_populosa["nome"] if equipe_mais_populosa else None,
            "equipe_maior_membros": equipe_mais_populosa["membros"] if equipe_mais_populosa else 0,
        },
        "equipes": equipes,
    }


@router.get("/form-data", response_model=dict)
def get_form_data(
        query: str = "",
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user)
    ):
    team_ids = _current_team_ids(db, current_user.user_id)
    normalized_query = query.strip()

    suggested_members = []
    if team_ids:
        suggested_rows = (
            db.query(
                Usuario.user_id,
                Usuario.nome,
                Usuario.email,
                func.count(func.distinct(UsuarioEquipe.team_id)).label("equipes_compartilhadas"),
            )
            .join(UsuarioEquipe, UsuarioEquipe.user_id == Usuario.user_id)
            .filter(Usuario.user_id != current_user.user_id)
            .filter(UsuarioEquipe.team_id.in_(team_ids))
            .group_by(Usuario.user_id, Usuario.nome, Usuario.email)
            .order_by(desc("equipes_compartilhadas"), Usuario.nome)
            .all()
        )

        suggested_members = [
            {
                "user_id": row.user_id,
                "nome": row.nome,
                "email": row.email,
                "equipes_compartilhadas": int(row.equipes_compartilhadas or 0),
            }
            for row in suggested_rows
        ]

    linked_user_ids = []
    if team_ids:
        linked_user_ids = [
            row.user_id
            for row in (
                db.query(UsuarioEquipe.user_id)
                .filter(UsuarioEquipe.team_id.in_(team_ids))
                .distinct()
                .all()
            )
        ]

    available_users_query = db.query(
        Usuario.user_id,
        Usuario.nome,
        Usuario.email,
    ).filter(Usuario.user_id != current_user.user_id)

    if linked_user_ids:
        available_users_query = available_users_query.filter(~Usuario.user_id.in_(linked_user_ids))

    if normalized_query:
        search_term = f"%{normalized_query}%"
        available_users_query = available_users_query.filter(
            or_(
                Usuario.nome.ilike(search_term),
                Usuario.email.ilike(search_term),
            )
        )

    available_users = [
        {
            "user_id": row.user_id,
            "nome": row.nome,
            "email": row.email,
        }
        for row in available_users_query.order_by(Usuario.nome).limit(12).all()
    ]

    return {
        "membros_sugeridos": suggested_members,
        "usuarios_disponiveis": available_users,
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_team(
        payload: EquipeCreate,
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user)
    ):
    nome = payload.nome.strip()
    if not nome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O nome da equipe é obrigatório.",
        )

    cargo_lider = _get_cargo_lider(db)
    cargo_membro = _get_cargo_membro(db)

    equipe = Equipe(
        nome=nome,
        descricao=payload.descricao.strip() if payload.descricao else None,
    )
    db.add(equipe)
    db.flush()

    db.add(UsuarioEquipe(
        user_id=current_user.user_id,
        team_id=equipe.team_id,
        cargo_id=cargo_lider.cargo_id,
    ))

    membros_ids = []
    for membro_id in payload.membros_ids:
        if membro_id == current_user.user_id or membro_id in membros_ids:
            continue

        usuario = db.query(Usuario).filter(Usuario.user_id == membro_id).first()
        if not usuario:
            continue

        membros_ids.append(membro_id)
        db.add(UsuarioEquipe(
            user_id=membro_id,
            team_id=equipe.team_id,
            cargo_id=cargo_membro.cargo_id,
        ))

    db.commit()
    db.refresh(equipe)

    detalhe = _load_team_detail(db, current_user, equipe.team_id)
    return {
        "mensagem": "Equipe criada com sucesso.",
        "equipe": detalhe,
    }


@router.get("/{team_id}", response_model=dict)
def get_team_detail(
        team_id: int,
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user)
    ):
    detail = _load_team_detail(db, current_user, team_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipe não encontrada para o usuário atual.",
        )

    return detail