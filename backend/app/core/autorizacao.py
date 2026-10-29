"""Autorizacao por cargo e escopo de tenant (Fatia 5b).

A Fatia 5a instalou o filtro de `organizacao_id`, que impede cruzar empresas.
Falta o segundo filtro: o que o usuario pode fazer *dentro* da propria
organizacao. Estas regras ficam num modulo so, porque a versao anterior estava
espalhada por `documentos.py` e `equipes.py` e ja tinha divergido:

- `cargo_usuario_no_documento` resolvia o `team_id` pelo *primeiro membro* do
  vinculo, sem comparar organizacao, e comparava nivel na mao em cada rota.
- `create_team` aceitava qualquer autenticado.
"""

import logging
import os

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core import tenancy
from app.models.cargo import Cargo
from app.models.equipe import Equipe
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe

# Escala do banco: membro=1, supervisor=2, lider=3.
NIVEL_MEMBRO = 1
NIVEL_SUPERVISOR = 2
NIVEL_LIDER = 3

# Nivel minimo para reverter a censura e ver o original: padrao lider (3),
# ajustavel por SAFEMASK_NIVEL_MIN_DESCENSURA (PI-III #87). Use sempre
# nivel_min_descensura(); a constante e so o padrao.
NIVEL_MIN_DESCENSURA = NIVEL_LIDER
VARIAVEL_NIVEL_MIN_DESCENSURA = "SAFEMASK_NIVEL_MIN_DESCENSURA"

logger = logging.getLogger(__name__)


def nivel_min_descensura() -> int:
    """Nivel minimo do cargo para o original, lido a cada requisicao.

    Aceita 1 a 3, a mesma escala dos cargos; valor ausente ou invalido volta
    ao padrao (lider) e o log avisa.
    """
    valor = os.getenv(VARIAVEL_NIVEL_MIN_DESCENSURA, "").strip()
    if not valor:
        return NIVEL_MIN_DESCENSURA
    try:
        nivel = int(valor)
    except ValueError:
        nivel = 0
    if not NIVEL_MEMBRO <= nivel <= NIVEL_LIDER:
        logger.warning(
            "%s=%r invalido (aceito: %d a %d); usando %d.",
            VARIAVEL_NIVEL_MIN_DESCENSURA, valor, NIVEL_MEMBRO, NIVEL_LIDER, NIVEL_MIN_DESCENSURA,
        )
        return NIVEL_MIN_DESCENSURA
    return nivel


def equipe_do_usuario(db: Session, usuario: Usuario, team_id: int):
    """Vinculo do usuario com a equipe, ja restrito ao tenant dele."""
    return (
        db.query(UsuarioEquipe)
        .join(Equipe, Equipe.team_id == UsuarioEquipe.team_id)
        .filter(
            UsuarioEquipe.user_id == usuario.user_id,
            UsuarioEquipe.team_id == team_id,
            Equipe.organizacao_id == usuario.organizacao_id,
        )
        .first()
    )


def cargo_na_equipe(db: Session, usuario: Usuario, team_id: int) -> dict | None:
    """Cargo {nome, nivel} do usuario na equipe, ou None se ele nao pertence."""
    vinculo = equipe_do_usuario(db, usuario, team_id)
    if not vinculo:
        return None

    cargo = db.query(Cargo).filter(Cargo.cargo_id == vinculo.cargo_id).first()
    if not cargo:
        return None
    return {"nome": cargo.nome, "nivel": int(cargo.nivel)}


def maior_cargo(db: Session, usuario: Usuario) -> dict | None:
    """Cargo mais alto do usuario em qualquer equipe *da sua* organizacao.

    `get_current_user` ja limita a consulta a `organizacao_id` do token, mas
    aqui o filtro e explicito: o cargo vem de um vinculo, e vinculo sem escopo
    seria exatamente o vazamento que a Fatia 5a fechou.
    """
    organizacao_id = tenancy.exigir_organizacao(usuario)
    linha = (
        db.query(Cargo.nome, Cargo.nivel)
        .join(UsuarioEquipe, UsuarioEquipe.cargo_id == Cargo.cargo_id)
        .join(Equipe, Equipe.team_id == UsuarioEquipe.team_id)
        .filter(
            UsuarioEquipe.user_id == usuario.user_id,
            Equipe.organizacao_id == organizacao_id,
        )
        .order_by(Cargo.nivel.desc())
        .first()
    )
    if not linha:
        return None
    return {"nome": linha.nome, "nivel": int(linha.nivel)}


def tem_gestao(db: Session, usuario: Usuario) -> bool:
    """O usuario supervisa ou lidera alguma equipe da propria organizacao?"""
    cargo = maior_cargo(db, usuario)
    return cargo is not None and cargo["nivel"] >= NIVEL_SUPERVISOR


def exigir_gestao(db: Session, usuario: Usuario):
    """Exige supervisao/lideranca em alguma equipe; 403 caso contrario.

    Usado por `create_team`. Criar equipe nao era gesto livre antes: qualquer
    conta recem-registrada criava um time e ja nascia lider, destravando
    descensura (nivel 3) sobre os proprios documentos.
    """
    tenancy.exigir_organizacao(usuario)
    cargo = maior_cargo(db, usuario)
    if cargo is None or cargo["nivel"] < NIVEL_SUPERVISOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas supervisores ou líderes podem criar equipes.",
        )
    return cargo
