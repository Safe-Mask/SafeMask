r"""Onde ficam os arquivos dos documentos.

Antes, `uploads/` era relativo ao diretorio de execucao: a API so achava os
arquivos se fosse iniciada de dentro de backend/. Agora:

- a pasta vem de SAFEMASK_PASTA_UPLOADS; caminho relativo parte de backend/,
  nunca do diretorio atual;
- sem a variavel, a pasta e backend/uploads, resolvida a partir deste
  arquivo: o mesmo lugar de antes para quem rodava de dentro de backend/;
- o arquivo e localizado pelo NOME dentro da pasta configurada, entao mover a
  pasta inteira (por exemplo, para o disco de dados do servidor) nao exige
  mexer no banco. Registros antigos, com `uploads/censurados/...` ou com
  caminho absoluto, continuam valendo.

No servidor (PLANO_SERVIDOR.md), a variavel aponta para o disco de dados,
fora da pasta do codigo, para que uma nova versao nao apague os arquivos.
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#24, ADR 0005 de la).
"""

import os
from pathlib import Path, PureWindowsPath

VARIAVEL_PASTA = "SAFEMASK_PASTA_UPLOADS"
BACKEND_DIR = Path(__file__).resolve().parents[2]
PASTA_PADRAO = BACKEND_DIR / "uploads"


def pasta_uploads() -> Path:
    valor = os.getenv(VARIAVEL_PASTA, "").strip()
    if not valor:
        return PASTA_PADRAO
    pasta = Path(valor).expanduser()
    if not pasta.is_absolute():
        pasta = BACKEND_DIR / pasta
    return pasta.resolve()


def preparar(base: Path) -> tuple[Path, Path]:
    """Cria (se faltar) e devolve as subpastas `originais` e `censurados`."""
    originais, censurados = base / "originais", base / "censurados"
    originais.mkdir(parents=True, exist_ok=True)
    censurados.mkdir(parents=True, exist_ok=True)
    return originais, censurados


def nome_do_arquivo(caminho_storage: str) -> str:
    r"""Nome do arquivo em `caminho_storage`, com separador do Windows ou do Linux.

    PureWindowsPath aceita as duas barras; Path, no Linux, trataria
    `uploads\censurados\x.pdf` como um nome so.
    """
    return PureWindowsPath(caminho_storage).name
