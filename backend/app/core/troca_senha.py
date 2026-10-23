"""Reforco da troca de senha obrigatoria no primeiro acesso.

O admin semeadado no 1o boot (`app.core.seed_instalacao`) nasce com
`precisa_trocar_senha=True`. Enquanto o flag nao cair, tudo fora de `/auth`
responde 403 — o client usa isso para abrir a tela de troca antes de
qualquer outra coisa, e um token vazado do admin provisorio nao vale nada.

O middleware e leve por proposito: le o `sub` do JWT (sem validar cargo) e
confere so o flag; a autorizacao real fica nas rotas, como sempre.
OPTIONS passa (preflight), e caminhos de /auth ficam livres para o proprio
login/troca.
"""

from __future__ import annotations

import logging

from jose import JWTError
from starlette.responses import JSONResponse

from app.core.security import ALGORITHM, SECRET_KEY
from app.database import SessionLocal
from app.models import Usuario

logger = logging.getLogger(__name__)

MENSAGEM = (
    "Troque a senha inicial antes de usar o servico. "
    "Use POST /auth/trocar-senha."
)


def _token_do_header(headers) -> str | None:
    """Valor do token em `Authorization: Bearer <token>`, ou None."""
    for chave, valor in headers:  # headers: list[(bytes, bytes)]
        if chave.decode("latin-1").lower() == "authorization":
            partes = valor.decode("latin-1").split(" ", 1)
            if len(partes) == 2 and partes[0].lower() == "bearer":
                return partes[1]
            return None
    return None


def usuario_com_troca_pendente(token: str | None) -> bool:
    """True se o token e valido e o usuario ainda precisa trocar a senha."""
    if not token:
        return False
    try:
        from jose import jwt

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return False
    email = payload.get("sub")
    if not email:
        return False

    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        return bool(usuario is not None and usuario.precisa_trocar_senha)
    finally:
        db.close()


class MiddlewareTrocaSenhaObrigatoria:
    """ASGI middleware que recusa o resto da API a troca de senha pendente."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("method") != "OPTIONS":
            if not scope.get("path", "").startswith("/auth"):
                token = _token_do_header(scope.get("headers") or [])
                if usuario_com_troca_pendente(token):
                    resposta = JSONResponse(
                        status_code=403,
                        content={"detail": MENSAGEM},
                        headers={"Cache-Control": "no-store"},
                    )
                    await resposta(scope, receive, send)
                    return
        await self.app(scope, receive, send)
