"""Configuracao do servico instalado na empresa (service.yaml).

1 instalacao = 1 empresa (veja `PLANO_DESKTOP.md`): quem instala aponta a
pasta base da rede (onde caem os documentos da empresa), a porta da API e o
nome da equipe padrao que recebe a ingestao automatica.

Fonte de valores, da mais fraca para a mais forte:
  1. Defaults deste modulo (watch desligado, porta 8000)
  2. `service.yaml` ao lado do executavel (no pacote PyInstaller) ou no cwd
  3. Variaveis de ambiente `SERVICE_*` (dev/teste e casos especiais)

Um service.yaml invalido nao derruba o boot: o servico sobe com defaults e
registra o problema no log, ou o admin perde o acesso e nao descobre nunca.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

NOME_ARQUIVO = "service.yaml"

# Intervalo entre varreduras da pasta base (segundos). Watch em share de rede
# perde eventos as vezes; o polling por hash e o arquivo camada garantida.
INTERVALO_WATCH_PADRAO = 10

# Nome da equipe padrao que recebe a ingestao automatica da pasta base.
EQUIPE_PADRAO_PADRAO = "Documentos da empresa"


@dataclass
class ConfigService:
    """Valores resolvidos de instalacao. `pasta_base` None = watch desligado."""

    pasta_base: Path | None = None
    porta: int = 8000
    equipe_padrao: str = EQUIPE_PADRAO_PADRAO
    intervalo_watch: int = INTERVALO_WATCH_PADRAO
    origem: str = "padroes"
    invalida: list[str] = field(default_factory=list)

    def descritor(self) -> str:
        pasta = str(self.pasta_base) if self.pasta_base else "(desligado)"
        return f"pasta_base={pasta} porta={self.porta} equipe={self.equipe_padrao!r}"


def _caminho_yaml() -> Path | None:
    """service.yaml ao lado do executavel empacotado (ou no cwd em dev)."""
    if getattr(sys, "frozen", False):  # PyInstaller
        candidato = Path(sys.executable).resolve().parent / NOME_ARQUIVO
        if candidato.is_file():
            return candidato
        return None
    local = Path.cwd() / NOME_ARQUIVO
    return local if local.is_file() else None


def _int(valor, chave: str, invalida: list[str]) -> int | None:
    """int > 0 a partir do yaml.

    Chave ausente (`None`) nao e erro; valor vazio ou lixo e, sim.
    """
    if valor is None:
        return None
    try:
        numero = int(valor)
        if numero <= 0:
            raise ValueError
        return numero
    except (TypeError, ValueError):
        invalida.append(chave)
        return None


def _int_env(valor, chave: str, invalida: list[str]) -> int | None:
    """`SERVICE_*`: enviadas vazias ("" / unset) contam como ausentes."""
    if valor in (None, ""):
        return None
    return _int(valor, chave, invalida)


def _yaml_para_config(dados: dict, config: ConfigService) -> None:
    if not isinstance(dados, dict):
        config.invalida.append(NOME_ARQUIVO)
        return

    pasta = dados.get("pasta_base")
    if pasta in (None, ""):
        pass  # watch fica desligado
    elif isinstance(pasta, str):
        config.pasta_base = Path(pasta).expanduser()
    else:
        config.invalida.append("pasta_base")

    porta = _int(dados.get("porta"), "porta", config.invalida)
    if porta:
        config.porta = porta

    intervalo = _int(
        dados.get("intervalo_watch"), "intervalo_watch", config.invalida
    )
    if intervalo:
        config.intervalo_watch = intervalo

    equipe = dados.get("equipe_padrao")
    if equipe is None:
        pass
    elif isinstance(equipe, str) and equipe.strip():
        config.equipe_padrao = equipe.strip()
    else:
        config.invalida.append("equipe_padrao")


def carregar(env: dict | None = None) -> ConfigService:
    """Resolve a configuracao efetiva. `env` permite testes sem monkeypatch."""
    env = env if env is not None else os.environ
    config = ConfigService()

    caminho = _caminho_yaml()
    if caminho is not None:
        import yaml

        try:
            dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - qualquer yaml quebrado cai no default
            config.invalida.append(f"{NOME_ARQUIVO} ilegivel ({exc})")
            dados = None
        if dados is not None:
            _yaml_para_config(dados, config)
        config.origem = f"{NOME_ARQUIVO} ({caminho})"

    # Env sobrepoe o yaml: dev/teste sem tocar o yaml da instalacao.
    pasta_env = env.get("SERVICE_PASTA_BASE")
    if pasta_env == "":
        pass
    elif pasta_env:
        config.pasta_base = Path(pasta_env).expanduser()
        config.origem = f"{config.origem} + SERVICE_PASTA_BASE"

    porta_env = _int_env(env.get("SERVICE_PORTA"), "SERVICE_PORTA", config.invalida)
    if porta_env:
        config.porta = porta_env

    intervalo_env = _int_env(
        env.get("SERVICE_INTERVALO_WATCH"), "SERVICE_INTERVALO_WATCH", config.invalida
    )
    if intervalo_env:
        config.intervalo_watch = intervalo_env

    equipe_env = env.get("SERVICE_EQUIPE_PADRAO")
    if equipe_env and equipe_env.strip():
        config.equipe_padrao = equipe_env.strip()

    if config.invalida:
        logger.warning(
            "Configuracao parcialmente invalida (%s); valores invalidos foram "
            "ignorados: %s. Fixe o service.yaml.",
            config.origem,
            ", ".join(config.invalida),
        )
    return config
