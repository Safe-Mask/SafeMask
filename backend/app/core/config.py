"""Configuracao central da API.

Antes as opcoes de rede e upload estavam hardcoded nas rotas. Este modulo le
do ambiente e expoe valores com default seguro, para que o comportamento em
producao dependa de variavel explicita e nao de edicao de codigo.
"""

import logging
import os
from urllib.parse import urlsplit

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


def _normalizar_origens(bruto: str) -> list[str]:
    return [item.strip().rstrip("/") for item in bruto.split(",") if item.strip()]


def _lista_env(chave: str, padrao: str = "") -> list[str]:
    return _normalizar_origens(os.getenv(chave, padrao))


def _int_env(chave: str, padrao: int) -> int:
    try:
        return int(os.getenv(chave, padrao))
    except (TypeError, ValueError):
        logger.warning("%s invalida; usando %s", chave, padrao)
        return padrao


def _ambiente_desenvolvimento() -> bool:
    """True em dev/teste, onde localhost e um servidor local sao esperados."""
    return os.getenv("ENVIRONMENT", "development").lower() in {
        "development", "dev", "test", "testing", "local",
    }


def _origem_local(origem: str) -> bool:
    host = urlsplit(origem).hostname or ""
    return host in {"localhost", "127.0.0.1", "::1"}


def _origens_cors() -> list[str]:
    """Origens efetivas: padrao do projeto **unido** com FRONTEND_ORIGINS.

    Antes a env var substituia o padrao. Em producao ela so trazia
    safemask-frontend.vercel.app, safe-mask.vercel.app ficou de fora e o login
    morreu no navegador com "Disallowed CORS origin" (curl passava porque nao
    impoe CORS). Unir mantem os dominios do projeto sempre ativos e deixa a
    env var como lugar para acrescentar origens novas.

    Em producao (ENVIRONMENT fora de dev/teste) as origens de localhost sao
    descartadas: la so as origens reais do frontend tem sentido.
    """
    vistas: dict[str, None] = {}
    for origem in (
        *_normalizar_origens(_ORIGENS_PADRAO),
        *_lista_env("FRONTEND_ORIGINS"),
    ):
        vistas[origem] = None
    todas = list(vistas)

    if _ambiente_desenvolvimento():
        return todas

    reais = [origem for origem in todas if not _origem_local(origem)]
    if not reais:
        # Nao quebra o boot: derrubar a aplicacao por falta de variavel de
        # ambiente seria pior que o risco. Mas deixa o risco visivel no log,
        # porque localhost em producao aceita XHR de qualquer app local.
        logger.error(
            "Nenhuma origem de frontend em producao; mantendo o padrao "
            "completo (inclui localhost). Defina FRONTEND_ORIGINS."
        )
        return todas
    return reais


CORS_ORIGINS: list[str] = _origens_cors()

# Em desenvolvimento as bancadas servem o frontend em portas variadas
# (python -m http.server 8080, Live Server 5501, Vite 3000...). Em vez de
# listar porta por porta, aceitamos qualquer origem localhost/127.0.0.1 com
# regex — que é desativado em produção, onde só valem os domínios reais.
_RegexLocalHost = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"


def _cors_origin_regex() -> str | None:
    if _ambiente_desenvolvimento():
        return _RegexLocalHost
    return None


CORS_ORIGIN_REGEX: str | None = _cors_origin_regex()

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
