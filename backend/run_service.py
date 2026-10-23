"""Entrada do servico empacotado (PyInstaller).

Esse arquivo e o entrypoint do exe no servidor da empresa: sobe
`app.main:app` na porta do service.yaml, escutando na rede interna.

Uso equivalente em dev:
  .venv/bin/uvicorn app.main:app --port 8000
"""

import uvicorn

from app.core.service_config import carregar


def principal() -> None:
    config = carregar()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.porta,
        log_level="info",
    )


if __name__ == "__main__":
    principal()
