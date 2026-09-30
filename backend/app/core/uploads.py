"""Validacao de arquivos enviados pelo usuario."""

from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import (
    ALLOWED_UPLOAD_SUFFIXES,
    MAX_UPLOAD_BYTES,
    PDF_MAGIC,
)

# Quantos bytes sao lidos para checar a assinatura do arquivo.
AMOSTRA_ASSINATURA = 8


def validar_nome_arquivo(nome: str | None) -> Path:
    """Valida a extensao e devolve o Path do nome.

    Nao confia em `filename`: o cliente pode mandar qualquer coisa. A checagem
    de conteudo fica em `validar_conteudo_pdf`.
    """
    if not nome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de arquivo ausente.",
        )

    caminho = Path(nome)
    if caminho.suffix.lower() not in ALLOWED_UPLOAD_SUFFIXES:
        aceitos = ", ".join(sorted(ALLOWED_UPLOAD_SUFFIXES))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato nao aceito. Envie apenas: {aceitos}.",
        )
    return caminho


def validar_conteudo_pdf(conteudo: bytes) -> None:
    """Rejeita arquivo vazio, grande demais ou que nao e PDF de verdade."""
    if not conteudo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio.",
        )

    if len(conteudo) > MAX_UPLOAD_BYTES:
        limite_mb = MAX_UPLOAD_BYTES / 1024 / 1024
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo excede o limite de {limite_mb:.0f} MB.",
        )

    if not conteudo.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O conteudo enviado nao e um PDF valido.",
        )


async def ler_e_validar_upload(file: UploadFile, nome_saida: Path) -> tuple[bytes, Path]:
    """Valida `file`, devolve (conteudo, extensao) e nao escreve nada em disco.

    O chamador decide onde gravar, para que a validacao possa rodar antes de
    qualquer escrita no storage.
    """
    caminho = validar_nome_arquivo(file.filename)
    conteudo = await file.read()
    validar_conteudo_pdf(conteudo)
    return conteudo, caminho