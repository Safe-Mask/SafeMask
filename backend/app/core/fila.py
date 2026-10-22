"""Fila de processamento em background (scan/OCR) com agendador testavel.

O upload em lote responde rapidamente: cada arquivo entra como Documento
`AGUARDANDO` e o scan (pesado, com OCR) roda depois. Mais de um worker satura
a CPU de maquinas pequenas com Tesseract, entao o padrao e 1 (FILA_WORKERS).

Nos testes, um fixture instala um agendador sincrono: `agendar` roda a task
antes de responder a requisicao, e o resultado aparece no banco sem espera.
"""

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


def _int_env(chave: str, padrao: int) -> int:
    try:
        return int(os.getenv(chave, str(padrao)))
    except (TypeError, ValueError):
        logger.warning("%s invalida; usando %s", chave, padrao)
        return padrao


# Scan/OCR e pesado: o alvo e servidor de empresa, so com Tesseract.
_MAX_WORKERS = max(1, min(2, _int_env("FILA_WORKERS", 1)))

_executor: ThreadPoolExecutor | None = None
_futuros: list = []
_trava = threading.Lock()
# Injetado pelos testes para robamente rodar a task inline.
_agendador = None  # callable(funcao, *args) -> None


def agendar(funcao, *args) -> None:
    """Executa `funcao(*args)` no agendador injetado, ou na fila de threads.

    Nunca levanta excecao no agendamento: o processamento por arquivo ja trata
    os proprios erros, e uma falha daqui derrubaria a resposta HTTP inteira.
    """
    global _executor
    try:
        with _trava:
            agendador = _agendador
            futuro = None
            if agendador is None:
                if _executor is None:
                    _executor = ThreadPoolExecutor(
                        max_workers=_MAX_WORKERS, thread_name_prefix="safemask-scan"
                    )
                futuro = _executor.submit(funcao, *args)
                _futuros.append(futuro)
        if agendador is not None:
            agendador(funcao, *args)
    except Exception:
        logger.exception("Falha ao agendar tarefa da fila: %r", funcao)


def esperar_termino(timeout: float = 60.0) -> None:
    """Espera as tarefas pendentes terminarem (testes e desligamento)."""
    with _trava:
        futuros = list(_futuros)
        _futuros.clear()
    for futuro in futuros:
        futuro.result(timeout=timeout)


def definir_agendador(agendador) -> None:
    """Instala/remove um agendador alternativo (None volta ao ThreadPool)."""
    global _agendador
    with _trava:
        _agendador = agendador


def desligar() -> None:
    """Encerra o executor aguardando as tarefas pendentes."""
    global _executor
    with _trava:
        executor = _executor
        _executor = None
    if executor is not None:
        esperar_termino()
        executor.shutdown(wait=True)
