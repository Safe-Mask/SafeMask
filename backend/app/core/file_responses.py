"""Respostas de arquivo que carregam conteudo do usuario.

Arquivos enviados passam por `validar_conteudo_pdf`, que exige o cabecalho
`%PDF-`. Isso so garante que o arquivo *comeca* como PDF: um PDF pode embutir
JavaScript (`/JavaScript`, `/OpenAction`) e acoes (`/Launch`). Servir isso
`inline` sob a mesma origem da aplicacao permite que o script do PDF rode com
as credenciais de quem abriu o preview.

Por isso as rotas usam `responder_arquivo` em vez de `FileResponse` direto:
alema de forcar `application/pdf` (nunca o que o `mimetypes` adivinhar do
nome) e `Content-Disposition: attachment`, a resposta traz `nosniff` e uma CSP
que bloqueia script. O arquivo continua sendo exibivel no `<embed>`/`<object>`
do preview, sem executar.
"""

from pathlib import Path

from fastapi.responses import FileResponse

# Um PDF pode carregar script; a CSP abaixo impede que ele execute mesmo que o
# navegador tente tratar a resposta como documento.
CSP_ARQUIVO = (
    "default-src 'none'; "
    "sandbox; "
    "script-src 'none'; "
    "object-src 'none'; "
    "frame-ancestors 'self'"
)

MEDIA_TYPE_PDF = "application/pdf"


def responder_arquivo(
    caminho: Path,
    nome_para_download: str,
    *,
    inline: bool = False,
) -> FileResponse:
    """Resposta de arquivo com travas contra execucao de conteudo enviado.

    `inline=False` (padrao) baixa o arquivo. `inline=True` mantem a exibicao
    para o preview, mas ainda com `attachment` como fallback em `preview_url`:
    quem abre a URL direto recebe download, e o preview so funciona porque o
    `<embed>` renderiza sem depender do Content-Disposition.
    """
    resposta = FileResponse(
        path=str(caminho),
        # Forcado em vez dopalpite do mimetypes: um `.pdf` com conteudo
        # arbitrario nunca deve ser servido como `text/html`.
        media_type=MEDIA_TYPE_PDF,
        filename=nome_para_download,
        content_disposition_type="inline" if inline else "attachment",
    )
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["Content-Security-Policy"] = CSP_ARQUIVO
    return resposta
