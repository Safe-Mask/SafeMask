"""Seed de instalacao: organizacao unica, admin e equipe padrao no 1o boot.

1 instalacao = 1 empresa. Instalado no servidor da empresa, o servico cria
sozinho a organizacao, o admin e a equipe que recebe a ingestao da pasta
base — a TI roda o exe e acessa o client no primeiro dia.

O admin nasce com senha temporaria gerada no boot, impressa no log SO DO
BOOT (quem instalou esta na maquina) e com `precisa_trocar_senha=True`: as
rotas fora de `/auth` recusam enquanto a senha nao for trocada
(`app.routes.auth.reforcar_troca_obrigatoria`).

Idempotente: admin existente (ou qualquer usuario) => nada e criado.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.core import tenancy
from app.core.security import hash_senha
from app.models import Cargo, Equipe, Usuario, UsuarioEquipe

logger = logging.getLogger("safemask.seed")

# Dominio no padrao `*.example.com`: dominio `.local` e rejeitado pela
# validacao de e-mail (EmailStr) e este aqui precisa passar pelo /auth/login
# no 1o uso. Trocavel depois pelo admin.
ADMIN_EMAIL_PADRAO = "admin@safemask.example.com"
EQUIPE_PADRAO_SEED_NOME = "Documentos da empresa"

# 16 caracteres urlsafe: curtos o bastante para digitar a mao e aleatorios o
# bastante para cruzar os dias entre a instalacao e a troca de senha.
TAMANHO_SENHA_INICIAL = 16


def senha_inicial_nova() -> str:
    """Senha provisionaria do admin provisorio. Cada instalacao gera a sua."""
    return secrets.token_urlsafe(TAMANHO_SENHA_INICIAL)


def _cargo_lider(db: Session) -> Cargo:
    cargo = db.query(Cargo).filter(Cargo.nome == "lider").first()
    if cargo:
        return cargo
    cargo = Cargo(
        nome="lider", nivel=3,
        descricao="Gerencia equipe, define cargos e adiciona membros",
    )
    db.add(cargo)
    db.flush()
    return cargo


def semear(db: Session, senha_inicial: str | None = None) -> dict | None:
    """Garante organizacao unica + admin + equipe padrao. Idempotente.

    Devolve o admin criado ou None quando a instalacao ja tem usuario.
    Roda somente com o banco vazio de usuarios: indicio de instalacao nova.
    `senha_inicial` permite injecao em testes; sem ele, gera uma aleatoria.
    `senha_inicial` permite inject em testes; sem ele, gera uma aleatoria.
    """
    if db.query(Usuario).first() is not None:
        db.commit()
        return None

    if senha_inicial is None:
        senha_inicial = senha_inicial_nova()

    organizacao = tenancy.carregar_organizacao_unica(db)

    admin = Usuario(
        nome="Administrador",
        email=ADMIN_EMAIL_PADRAO,
        senha_hash=hash_senha(senha_inicial),
        organizacao_id=organizacao.organizacao_id,
        precisa_trocar_senha=True,
        criado_em=datetime.utcnow(),
    )
    db.add(admin)
    db.flush()

    equipe = Equipe(
        nome=EQUIPE_PADRAO_SEED_NOME,
        descricao="Recebe a ingestao automatica da pasta base",
        organizacao_id=organizacao.organizacao_id,
        criado_em=datetime.utcnow(),
    )
    db.add(equipe)
    db.flush()

    db.add(UsuarioEquipe(
        user_id=admin.user_id,
        team_id=equipe.team_id,
        cargo_id=_cargo_lider(db).cargo_id,
        criado_em=datetime.utcnow(),
    ))
    db.commit()
    db.refresh(admin)

    logger.warning(
        "*** INSTALACAO NOVA *** admin provisorio criado: email=%s senha=%s -- "
        "troque essa senha no primeiro acesso (o servico exige). "
        "Este aviso aparece apenas na instalacao nova.",
        ADMIN_EMAIL_PADRAO, senha_inicial,
    )
    return admin
