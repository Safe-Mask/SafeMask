
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.core import autorizacao, tenancy
from app.core.audit import (
    ACAO_ADICIONAR_MEMBRO,
    ACAO_ALTERAR_CARGO,
    ACAO_REMOVER_MEMBRO,
    RESULTADO_NEGADO,
    registrar,
)
from app.core.current_user import get_current_user
from app.core.datas import iso_utc
from app.database import get_db
from app.models.cargo import Cargo
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from app.schemas.equipe import EquipeCreate, EquipeMembroAdd, EquipeMembroCargo

router = APIRouter(prefix="/equipes", tags=["Equipes"])


def _current_team_ids(db: Session, user_id: int) -> list[int]:
    return [
        row.team_id
        for row in (
            db.query(UsuarioEquipe.team_id)
            .filter(UsuarioEquipe.user_id == user_id)
            .distinct()
            .all()
        )
    ]


def _get_cargo_by_name(db: Session, nomes: list[str]) -> Cargo | None:
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
        "criado_em": iso_utc(member_row.criado_em),
    }


def _load_team_detail(db: Session, current_user: Usuario, team_id: int):
    team_row = (
        db.query(
            Equipe.team_id,
            Equipe.organizacao_id,
            Equipe.nome,
            Equipe.descricao,
            Equipe.criado_em,
        )
        .join(UsuarioEquipe, UsuarioEquipe.team_id == Equipe.team_id)
        .filter(
            Equipe.team_id == team_id,
            UsuarioEquipe.user_id == current_user.user_id,
            # Defesa em profundidade: o vinculo de equipe ja restringe, mas a
            # equipe tambem precisa pertencer a organizacao de quem pede.
            Equipe.organizacao_id == tenancy.exigir_organizacao(current_user),
        )
        .first()
    )

    if not team_row:
        return None

    user_team_ids = [
        row.user_team_id
        for row in (
            db.query(UsuarioEquipe.user_team_id)
            .filter(
                UsuarioEquipe.team_id == team_id,
                UsuarioEquipe.user_id == current_user.user_id,
            )
            .all()
        )
    ]

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

    documentos_rows = (
        db.query(
            Documento.doc_id,
            Documento.nome_original,
            Documento.extensao,
            Documento.tamanho_bytes,
            Documento.nivel_seguranca,
            Documento.status_processamento,
            Documento.criado_em,
            Documento.user_team_id,
            Usuario.nome.label("autor_nome"),
            Cargo.nome.label("cargo_nome"),
        )
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .join(Usuario, Usuario.user_id == UsuarioEquipe.user_id)
        .join(Cargo, Cargo.cargo_id == UsuarioEquipe.cargo_id)
        .filter(UsuarioEquipe.team_id == team_id, Documento.ativo.is_(True))
        .order_by(Documento.criado_em.desc(), Documento.doc_id.desc())
        .all()
    )

    documentos = (
        db.query(func.count(func.distinct(Documento.doc_id)))
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(UsuarioEquipe.team_id == team_id, Documento.ativo.is_(True))
        .scalar()
        or 0
    )

    return {
        "team_id": team_row.team_id,
        "organizacao_id": team_row.organizacao_id,
        "nome": team_row.nome,
        "descricao": team_row.descricao,
        "criado_em": iso_utc(team_row.criado_em),
        "membros": len(members),
        "documentos": int(documentos),
        "membros_lista": [_serialize_member(member) for member in members],
        # A tela usa para mostrar (ou nao) o formulario de membros e os botoes
        # de remover. A API confere de novo em cada operacao.
        # Opcoes do seletor de cargo, do maior nivel para o menor.
        "cargos": [
            {"nome": cargo.nome, "nivel": int(cargo.nivel)}
            for cargo in db.query(Cargo).order_by(Cargo.nivel.desc(), Cargo.nome).all()
        ],
        "pode_gerenciar_membros": any(
            m.user_id == current_user.user_id and int(m.cargo_nivel or 0) >= autorizacao.NIVEL_LIDER
            for m in members
        ),
        "documentos_lista": [
            {
                "doc_id": row.doc_id,
                "nome_original": row.nome_original,
                "extensao": row.extensao,
                "tamanho_bytes": int(row.tamanho_bytes or 0),
                "nivel_seguranca": row.nivel_seguranca,
                "status_processamento": row.status_processamento,
                "criado_em": iso_utc(row.criado_em),
                "autor_nome": row.autor_nome,
                "cargo_nome": row.cargo_nome,
                "user_team_id": row.user_team_id,
                # Todo membro da equipe acessa o documento; o cargo decide nas
                # rotas de documento o que ele recebe. Antes so quem enviou o
                # documento via o botao liberado.
                "tem_acesso": bool(user_team_ids),
                "preview_url": f"/documentos/censurados/{row.doc_id}/arquivo" if user_team_ids else None,
            }
            for row in documentos_rows
        ],
    }


@router.get("/overview", response_model=dict)
def get_equipes_overview(
        db: Session = Depends(get_db),
        current_user: Usuario = Depends(get_current_user)
    ):
    # Esta consulta responde so "de quais equipes o usuario participa". Os
    # totais nao podem sair daqui: o filtro por user_id deixa uma linha de
    # usuario_equipe por equipe, e a contagem sobre essa juncao dava sempre 1
    # membro e so os documentos do proprio usuario. Os totais sao contados
    # por equipe, abaixo, com o mesmo criterio da pagina de detalhe.
    team_rows = (
        db.query(
            Equipe.team_id,
            Equipe.nome,
            Equipe.descricao,
            Equipe.criado_em,
        )
        .join(UsuarioEquipe, UsuarioEquipe.team_id == Equipe.team_id)
        .filter(UsuarioEquipe.user_id == current_user.user_id)
        .group_by(Equipe.team_id, Equipe.nome, Equipe.descricao, Equipe.criado_em)
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

        # Documentos de toda a equipe, nao apenas os enviados pelo usuario.
        total_documentos = (
            db.query(func.count(func.distinct(Documento.doc_id)))
            .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
            .filter(UsuarioEquipe.team_id == row.team_id)
            .scalar()
        )

        equipes.append({
            "team_id": row.team_id,
            "nome": row.nome,
            "descricao": row.descricao,
            "criado_em": iso_utc(row.criado_em),
            "membros": len(membros),
            "documentos": int(total_documentos or 0),
            "cargo_usuario": cargo_usuario,
            "membros_lista": membros,
        })

    # Mesma ordem de antes: mais membros primeiro, depois pelo nome.
    equipes.sort(key=lambda item: (-item["membros"], item["nome"]))

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
    organizacao_id = tenancy.exigir_organizacao(current_user)
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
    ).filter(
        Usuario.user_id != current_user.user_id,
        # Sugerir membros e listar usuarios e uma busca global. Sem este
        # filtro a tela de criar equipe oferecia usuarios de outras empresas.
        Usuario.organizacao_id == organizacao_id,
    )

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
    organizacao_id = tenancy.exigir_organizacao(current_user)

    # Quem cria a equipe vira lider dela. Antes isso valia para qualquer
    # autenticado: um membro comum criava um time e ja nascia lider, o que
    # destrava descensura (nivel 3) sobre os documentos dele.
    autorizacao.exigir_gestao(db, current_user)

    equipe = Equipe(
        nome=nome,
        descricao=payload.descricao.strip() if payload.descricao else None,
        organizacao_id=organizacao_id,
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

        # `membros_ids` vem do corpo da requisicao. Sem o filtro de tenant, um
        # lider poderia adicionar ao time alguem de outra organizacao.
        usuario = (
            db.query(Usuario)
            .filter(
                Usuario.user_id == membro_id,
                Usuario.organizacao_id == organizacao_id,
            )
            .first()
        )
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


# ------------------------------------------------------- gestao de membros


def _exigir_lider(
    db: Session,
    usuario: Usuario,
    team_id: int,
    acao: str,
    request: Request,
    mensagem: str = "Apenas o lider da equipe pode gerenciar os membros.",
) -> UsuarioEquipe:
    """Garante que quem chama e lider da equipe, na propria organizacao.

    Quem nao pertence a equipe recebe 404, e nao 403: confirmar que a equipe
    existe ja seria informacao para quem nao deveria ve-la. As duas recusas
    entram na trilha como "negado" (a de fora, so se a equipe for da mesma
    organizacao).
    """
    vinculo = autorizacao.equipe_do_usuario(db, usuario, team_id)
    if not vinculo:
        equipe = (
            db.query(Equipe.team_id)
            .filter(Equipe.team_id == team_id, Equipe.organizacao_id == usuario.organizacao_id)
            .first()
        )
        if equipe:
            registrar(db, request, usuario.user_id, acao, team_id=team_id, resultado=RESULTADO_NEGADO)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipe não encontrada para o usuário atual.",
        )

    cargo = db.query(Cargo).filter(Cargo.cargo_id == vinculo.cargo_id).first()
    if not cargo or cargo.nivel < autorizacao.NIVEL_LIDER:
        registrar(
            db, request, usuario.user_id, acao,
            team_id=team_id, cargo_id=vinculo.cargo_id, resultado=RESULTADO_NEGADO,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=mensagem)
    return vinculo


def _vinculo_na_equipe(db: Session, user_id: int, team_id: int) -> UsuarioEquipe | None:
    return (
        db.query(UsuarioEquipe)
        .filter(UsuarioEquipe.team_id == team_id, UsuarioEquipe.user_id == user_id)
        .first()
    )


def _outros_lideres(db: Session, team_id: int, user_id: int, cargo_lider: Cargo) -> int:
    return (
        db.query(func.count(UsuarioEquipe.user_team_id))
        .filter(
            UsuarioEquipe.team_id == team_id,
            UsuarioEquipe.user_id != user_id,
            UsuarioEquipe.cargo_id == cargo_lider.cargo_id,
        )
        .scalar()
        or 0
    )


@router.post("/{team_id}/membros", response_model=dict, status_code=status.HTTP_201_CREATED)
def adicionar_membro(
    team_id: int,
    payload: EquipeMembroAdd,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Adiciona uma pessoa da mesma organizacao a equipe, no cargo de membro.

    Entrar no menor privilegio e a escolha segura; promover e outra operacao.
    E-mail de outra organizacao recebe a mesma resposta de e-mail inexistente,
    para nao revelar quem esta cadastrado em outra empresa.
    """
    lider = _exigir_lider(db, current_user, team_id, ACAO_ADICIONAR_MEMBRO, request)

    email = payload.email.strip().lower()
    usuario = (
        db.query(Usuario)
        .filter(
            func.lower(Usuario.email) == email,
            Usuario.organizacao_id == current_user.organizacao_id,
        )
        .first()
    )
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não existe usuário com este e-mail na sua organização.",
        )

    if _vinculo_na_equipe(db, usuario.user_id, team_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este usuário já faz parte da equipe.")

    db.add(UsuarioEquipe(user_id=usuario.user_id, team_id=team_id, cargo_id=_get_cargo_membro(db).cargo_id))
    db.commit()

    # O alvo vai como user_id, nunca como o e-mail digitado.
    registrar(
        db, request, current_user.user_id, ACAO_ADICIONAR_MEMBRO,
        team_id=team_id, cargo_id=lider.cargo_id, alvo_user_id=usuario.user_id,
    )
    return {
        "mensagem": f"{usuario.nome} foi adicionado à equipe.",
        "equipe": _load_team_detail(db, current_user, team_id),
    }


@router.delete("/{team_id}/membros/{user_id}", response_model=dict)
def remover_membro(
    team_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Remove um membro da equipe.

    Duas recusas deliberadas:
    1. O ultimo lider nao sai: sem lider ninguem administra a equipe nem abre
       o original.
    2. Membro com documentos na equipe nao sai: o vinculo e o dono dos
       documentos (`Documento.user_team_id`), e apagar o vinculo apagaria os
       documentos junto.
    """
    lider = _exigir_lider(db, current_user, team_id, ACAO_REMOVER_MEMBRO, request)
    # Lido antes do delete: se o lider remover a si mesmo, o objeto some.
    cargo_do_lider = lider.cargo_id

    alvo = _vinculo_na_equipe(db, user_id, team_id)
    if not alvo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Este usuário não faz parte da equipe.")

    cargo_lider = _get_cargo_lider(db)
    if alvo.cargo_id == cargo_lider.cargo_id and _outros_lideres(db, team_id, user_id, cargo_lider) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A equipe ficaria sem líder. Promova outro membro antes de remover este.",
        )

    documentos = (
        db.query(func.count(Documento.doc_id)).filter(Documento.user_team_id == alvo.user_team_id).scalar() or 0
    )
    if documentos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Este membro possui {documentos} documento(s) na equipe. Remover o vínculo "
                "excluiria esses documentos, então a operação foi recusada."
            ),
        )

    db.delete(alvo)
    db.commit()

    registrar(
        db, request, current_user.user_id, ACAO_REMOVER_MEMBRO,
        team_id=team_id, cargo_id=cargo_do_lider, alvo_user_id=user_id,
    )
    return {
        "mensagem": "Membro removido da equipe.",
        "equipe": _load_team_detail(db, current_user, team_id),
    }


@router.patch("/{team_id}/membros/{user_id}", response_model=dict)
def alterar_cargo_membro(
    team_id: int,
    user_id: int,
    payload: EquipeMembroCargo,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Altera o cargo de um membro da equipe.

    O cargo decide o que a pessoa ve do documento (parcial e, para o lider, o
    original); a mudanca vale ja no proximo acesso. Recusas: so o lider altera
    (404/403, com evento "negado"); cargo inexistente ou igual ao atual (400);
    rebaixar o ultimo lider (400).
    """
    lider = _exigir_lider(db, current_user, team_id, ACAO_ALTERAR_CARGO, request)
    # Lido antes da alteracao: o lider pode estar rebaixando a si mesmo, e o
    # evento registra o cargo com que agiu.
    cargo_do_lider = lider.cargo_id

    alvo = _vinculo_na_equipe(db, user_id, team_id)
    if not alvo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Este usuário não faz parte da equipe.")

    novo_cargo = db.query(Cargo).filter(func.lower(Cargo.nome) == payload.cargo.strip().lower()).first()
    if not novo_cargo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cargo inexistente.")

    if alvo.cargo_id == novo_cargo.cargo_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Este membro já tem o cargo {novo_cargo.nome}.",
        )

    cargo_lider = _get_cargo_lider(db)
    if alvo.cargo_id == cargo_lider.cargo_id and _outros_lideres(db, team_id, user_id, cargo_lider) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A equipe ficaria sem líder. Promova outro membro a líder antes.",
        )

    alvo.cargo_id = novo_cargo.cargo_id
    db.commit()

    registrar(
        db, request, current_user.user_id, ACAO_ALTERAR_CARGO,
        team_id=team_id, cargo_id=cargo_do_lider, alvo_user_id=user_id,
    )
    nome_alvo = db.query(Usuario.nome).filter(Usuario.user_id == user_id).scalar()
    return {
        "mensagem": f"{nome_alvo} agora tem o cargo {novo_cargo.nome}.",
        "equipe": _load_team_detail(db, current_user, team_id),
    }
