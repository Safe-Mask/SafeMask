"""Organizacao unica: 1 instalacao do SafeMask = 1 empresa.

Com a virada on-premise (veja `PLANO_DESKTOP.md`) nao existe mais SaaS
multi-tenant: todo o banco pertence a uma organizacao so, criada no primeiro
cadastro. O filtro por `organizacao_id` continua nas rotas (defesa em
profundidade e congruencia com o schema existente), mas sempre aponta para a
mesma organizacao.

`Cargo` continua global de proposito: ele descreve papel (lider, supervisor,
membro), nao dado de cliente, e e populado no boot.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.organizacao import Organizacao
from app.models.usuario import Usuario

# Nome da organizacao unica. Criada no primeiro cadastro; quem cadastrar
# depois tambem entra nela, pois a instalacao serve uma empresa so.
ORGANIZACAO_UNICA_NOME = "SafeMask"


def carregar_organizacao_unica(db: Session, *, commit: bool = False) -> Organizacao:
    """A organizacao da instalacao, criando-a se ainda nao existir."""
    organizacao = db.query(Organizacao).order_by(Organizacao.organizacao_id).first()
    if organizacao:
        return organizacao

    organizacao = Organizacao(nome=ORGANIZACAO_UNICA_NOME)
    db.add(organizacao)
    if commit:
        db.commit()
    else:
        db.flush()
    return organizacao


def exigir_organizacao(usuario: Usuario) -> int:
    """Organizacao do usuario, ou erro se ele nao estiver vinculado a nenhuma.

    Um usuario sem organizacao seria um estado inconsistente, e devolver 403
    e melhor do que responder vazio e fazer o usuario acreditar que nao tem
    nada.
    """
    if usuario.organizacao_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não vinculado a uma organização.",
        )
    return usuario.organizacao_id
