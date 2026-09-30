"""Isolamento por organizacao (tenant).

A organizacao e o limite de dados: um usuario so enxerga equipes, membros e
documentos da propria organizacao. Este modulo concentra a resolucao do tenant
para que as rotas nao repitam a logica nem involem `usuario.organizacao_id`
direto.

`Cargo` continua global de proposito: ele descreve papel (lider, supervisor,
membro), nao dado de cliente, e e populado no boot.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.organizacao import Organizacao
from app.models.usuario import Usuario

# Destino dos dados que ja existiam antes da organizacao existir. Colocar tudo
# numa unica organizacao preserva o comportamento atual: nenhuma equipe ja
# existente passa a sumir do menu do seu usuario.
ORGANIZACAO_LEGADA_NOME = "SafeMask (dados anteriores)"


def buscar_ou_criar(db: Session, nome: str, *, commit: bool = False) -> Organizacao:
    """Organizacao pelo nome, criando se ainda nao existir.

    O nome nao e unico no schema: duas empresas podem se chamar igual, entao
    desambiguamos pelo menor id criado.
    """
    organizacao = (
        db.query(Organizacao)
        .filter(Organizacao.nome == nome)
        .order_by(Organizacao.organizacao_id)
        .first()
    )
    if organizacao:
        return organizacao

    organizacao = Organizacao(nome=nome)
    db.add(organizacao)
    if commit:
        db.commit()
    else:
        db.flush()
    return organizacao


def exigir_organizacao(usuario: Usuario) -> int:
    """Organizacao do usuario, ou erro se ele nao estiver vinculado a nenhuma.

    Depois da migracao todo usuario tem organizacao. Um usuario sem ela seria
    um estado inconsistente, e devolver 403 e melhor do que responder vazio e
    fazer o usuario acreditar que nao tem nada.
    """
    if usuario.organizacao_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não vinculado a uma organização.",
        )
    return usuario.organizacao_id