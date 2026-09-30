"""Configuracao central da API.

Antes as opcoes de rede e upload estavam hardcoded nas rotas. Este modulo le
do ambiente e expoe valores com default seguro, para que o comportamento em
producao dependa de variavel explicita e nao de edicao de codigo.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Origens liberadas para CORS. `*` com allow_credentials e um erro: o
# navegador ignora o header e o proprio FastAPI documenta como invalido.
# Separe por virgula em FRONTEND_ORIGINS.
_ORIGENS_PADRAO = (
    "https://safe-mask.vercel.app,"
    "https://safemask-frontend.vercel.app,"
    "http://localhost:5500,"
    "http://localhost:3000"
)


def _lista_env(chave: str, padrao: str = "") -> list[str]:
    bruto = os.getenv(chave, padrao)
    return [item.strip().rstrip("/") for item in bruto.split(",") if item.strip()]


def _int_env(chave: str, padrao: int) -> int:
    try:
        return int(os.getenv(chave, padrao))
    except (TypeError, ValueError):
        logger.warning("%s invalida; usando %s", chave, padrao)
        return padrao


CORS_ORIGINS: list[str] = _lista_env("FRONTEND_ORIGINS", _ORIGENS_PADRAO)

# URL publica do frontend, usada nos emails de recuperacao de senha.
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://safe-mask.vercel.app").rstrip("/")

# Tamanho maximo de upload. 20 MB e o teto do Vercel; acima disso o upload
# morre no proxy antes de chegar na aplicacao.
MAX_UPLOAD_BYTES: int = _int_env("MAX_UPLOAD_BYTES", 20 * 1024 * 1024)

# Assinatura de arquivo PDF (ISO 32000-1, Cabecalho 7.2).
PDF_MAGIC: bytes = b"%PDF-"

# Tipos aceitos no upload.
ALLOWED_UPLOAD_SUFFIXES: frozenset[str] = frozenset({".pdf"})

ACCESS_TOKEN_EXPIRE_MINUTES: int = _int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 120)
RESET_TOKEN_EXPIRE_MINUTES: int = _int_env("RESET_TOKEN_EXPIRE_MINUTES", 30)


def descrever() -> dict:
    """Resumo seguro para log no startup (nao expoe segredos)."""
    return {
        "cors_origins": CORS_ORIGINS,
        "frontend_url": FRONTEND_URL,
        "max_upload_mb": round(MAX_UPLOAD_BYTES / 1024 / 1024, 1),
        "access_token_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
    }
