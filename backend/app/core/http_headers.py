"""Headers de seguranca em toda resposta da API.

Os arquivos ja sao servidos com CSP e `nosniff`
(`app.core.file_responses`), mas as respostas JSON ficavam sem nenhum. Um
XSS ou uma injecao de HTML em qualquer pagina que renderize JSON nao tinha
nenhum header para deter, e o `Referer` padrao vaza a URL completa da API — que
carrega `doc_id` — para terceiros.
"""

from starlette.middleware.base import BaseHTTPMiddleware


class HeadersSegurancaMiddleware(BaseHTTPMiddleware):
    """Adiciona headers defensivos que nao dependem do tipo de resposta."""

    async def dispatch(self, request, call_next):
        resposta = await call_next(request)

        # `nosniff` impede que o navegador reinterprete o content-type. Ja era
        # aplicado nas respostas de arquivo; aqui vale para o JSON tambem.
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")

        # A API nunca deve ser embutida em frame de terceiros. Sem isto, um
        # site externo pode engradar a resposta e clicar em nome do usuario.
        resposta.headers.setdefault("X-Frame-Options", "DENY")

        # URL de API carrega `doc_id`, `team_id` e nomes de arquivo. Nao ha
        # motivo para mandar isso a terceiro junto do `Referer`.
        resposta.headers.setdefault("Referrer-Policy", "no-referrer")

        return resposta