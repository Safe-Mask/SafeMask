"""Cifra do original em disco (Fase 3.1 de `PLANO_DESKTOP.md`).

Premissa de compliance: o original NUNCA sai do servidor e, em disco, nao
fica legivel — cada arquivo em `originais/` nasce cifrado (Fernet, key =
AES128-CBC + HMAC-SHA256). A chave mora em `chave_original.key` junto do
servico (0600 onde o SO permite) e e criada uma vez no primeiro uso.

Quem PRECISA do original legivel (scan do lote na fila, descensura
parcial, entrega do original ao lider) materializa uma copia temporaria
com `materializar_original_para_leitura` e a descarta logo depois — o
plaintext vive dentro do request/processamento, nunca na pasta de
armazenamento.

Compatibilidade: arquivos gravados em texto puro de instalacoes anteriores
(ou dos testes) passam pelo mesmo caminho sem erro — deteccao pelo prefixo
`gAAA` do token do Fernet (nao casou = texto puro).
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

NOME_CHAVE = "chave_original.key"

# Indicio do token do Fernet: base64 comeca com "gAAA" (0x80 + timestamp).
# Compara 4 bytes e evita gastar validacao de HMAC quando nem cifra e.
_PREFIXO_TOKEN = b"gAAA"

_fernet_cache: Fernet | None = None


def caminho_da_chave() -> Path:
    """Arquivo de chave ao lado do exe (instalado) ou no cwd (dev)."""
    override = os.getenv("SAFEMASK_CHAVE_ARQUIVO")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):  # PyInstaller
        return Path(sys.executable).resolve().parent / NOME_CHAVE
    return Path.cwd() / NOME_CHAVE


def carregar() -> Fernet:
    """Chave da instalacao: carrega a existente ou cria uma vez so."""
    global _fernet_cache
    if _fernet_cache is not None:
        return _fernet_cache

    caminho = caminho_da_chave()
    if caminho.is_file():
        try:
            _fernet_cache = Fernet(caminho.read_bytes().strip())
            logger.info("Chave de cifragem do original em uso: %s", caminho)
        except ValueError as exc:
            raise RuntimeError(
                f"chave_original.key em {caminho} esta corrompida: sem ELA os "
                "originais cifrados sao ilegeis. Restaure o backup da chave "
                "antes de subir o servico."
            ) from exc
    else:
        nova = Fernet.generate_key()
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(nova)
        try:
            os.chmod(caminho, 0o600)
        except OSError:
            pass  # Windows/NTFS nao implementa chmod posix
        _fernet_cache = Fernet(nova)
        logger.warning(
            "*** CHAVE DE CIFRAGEM CRIADA: %s -- faca backup ANTES do 1o "
            "documento: sem a chave, os originais cifrados sao ilegeis.",
            caminho,
        )
    return _fernet_cache


def cifrar_bytes(conteudo: bytes) -> bytes:
    return carregar().encrypt(conteudo)


def e_cifrado(conteudo: bytes | None) -> bool:
    return conteudo is not None and conteudo.startswith(_PREFIXO_TOKEN)


class OrigemIlegivel(Exception):
    """O cifrado em disco nao abre com a chave desta instalacao."""


def _legivel_ou_erro(caminho: Path, bruto: bytes) -> bytes:
    try:
        return carregar().decrypt(bruto)
    except InvalidToken as exc:
        raise OrigemIlegivel(
            f"Original em {caminho} nao abre com a chave desta instalacao "
            "(chave_original.key trocada/perdida?)."
        ) from exc


def gravar_original_cifrado(destino: Path, conteudo: bytes) -> None:
    """Grava o original JA cifrado no lugar definitivo."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(cifrar_bytes(conteudo))


def decifrar_arquivo(caminho: Path) -> bytes:
    """Conteudo legivel do arquivo de origem (gravado cifrado ou puro)."""
    bruto = caminho.read_bytes()
    if not e_cifrado(bruto):
        return bruto
    return _legivel_ou_erro(caminho, bruto)


def materializar_original_para_leitura(caminho: Path) -> Path:
    """Copia legivel temporaria para quem precisa ler o arquivo por nome.

    Texto puro devolve o proprio caminho (sem copia); cifrado devolve temp
    no MESMO diretorio (nada cruza filesystem) — o chamador chama
    `descartar_material_temporario` no finally.
    """
    bruto = caminho.read_bytes()
    if not e_cifrado(bruto):
        return caminho

    legivel = _legivel_ou_erro(caminho, bruto)
    fd, nome = tempfile.mkstemp(
        prefix="cifra_", suffix=caminho.suffix or "", dir=caminho.parent
    )
    with os.fdopen(fd, "wb") as temp:
        temp.write(legivel)
    return Path(nome)


def descartar_material_temporario(temporario: Path, caminho_original: Path) -> None:
    """Apaga a temp da materializacao (sem tocar no original)."""
    if temporario == caminho_original:
        return  # estava em texto puro: nunca foi temp
    try:
        temporario.unlink(missing_ok=True)
    except OSError:
        logger.warning("Temp %s nao pôde ser apagado", temporario)


def migrar_originais_em_texto_puro(diretorio: Path) -> tuple[int, int]:
    """Cifra, no lugar, os originais legados que ainda estao em texto puro.

    Instalacoes anteriores a Fase 3.1 gravaram o original legivel. A migracao
    roda no boot do servico, e idempotente (arquivo ja cifrado e ignorado) e
    troca o conteudo de forma atomica (`os.replace`): uma queda no meio nao
    deixa original pela metade. Devolve (migrados, falhas).
    """
    if not diretorio.is_dir():
        return 0, 0

    migrados = 0
    falhas = 0
    for caminho in sorted(diretorio.iterdir()):
        if not caminho.is_file() or caminho.name.startswith(".cifra_"):
            continue
        try:
            bruto = caminho.read_bytes()
            if e_cifrado(bruto):
                continue
            temporario = caminho.with_name(f".cifra_{caminho.name}")
            try:
                temporario.write_bytes(cifrar_bytes(bruto))
                os.replace(temporario, caminho)
            finally:
                temporario.unlink(missing_ok=True)
            migrados += 1
        except OSError:
            logger.exception("Falha ao migrar original legado %s", caminho)
            falhas += 1

    if migrados:
        logger.warning(
            "Originais legados cifrados: %d em %s -- confira o backup da chave.",
            migrados, diretorio,
        )
    return migrados, falhas


if __name__ == "__main__":
    # Dev: `cd backend && .venv/bin/python -m app.core.cifra [pasta]`.
    # No servico empacotado quem chama e o run_service.py, antes do uvicorn.
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("uploads") / "originais"
    migrados, falhas = migrar_originais_em_texto_puro(destino)
    print(f"migrados={migrados} falhas={falhas} em {destino}")
