"""Revisao das tarjas antes de salvar (PI-III #208).

O upload detectava e ja gravava. Agora a tela pede antes a analise
(`POST /documentos/analisar`), mostra os achados e deixa a pessoa desmarcar
falsos positivos e acrescentar trechos. O envio leva os ids desmarcados e os
trechos; o scanner refaz a deteccao e aplica os ajustes.

Regras:
- o achado vai para a tela MASCARADO (`mascarar`): o dado inteiro nunca sai
  da API nesse caminho, nem fica gravado;
- os ajustes entram na auditoria so como contagens (`detalhe_da_revisao`);
- trechos acrescentados tem limite de quantidade e de tamanho.
"""

import json

from fastapi import HTTPException, status

MAX_TRECHOS = 20
TAMANHO_MIN_TRECHO = 3
TAMANHO_MAX_TRECHO = 120
MAX_IGNORADOS = 500

_MASCARA = "•"


def mascarar(valor: str, tipo: str | None = None) -> str:
    """Esconde o dado e mantem so a forma e o final.

    Letras e digitos viram `•`, menos os 2 ultimos (os 4 ultimos no cartao,
    como nos comprovantes). Pontuacao, espacos e `@` ficam, para a pessoa
    reconhecer o formato. Valor com ate 4 caracteres uteis e escondido inteiro.
    """
    valor = valor or ""
    uteis = [i for i, c in enumerate(valor) if c.isalnum()]
    manter = 0 if len(uteis) <= 4 else (4 if tipo == "CARTAO" else 2)
    visiveis = set(uteis[len(uteis) - manter:]) if manter else set()
    return "".join(c if (not c.isalnum() or i in visiveis) else _MASCARA for i, c in enumerate(valor))


def _lista_json(texto: str, campo: str) -> list:
    # Campo nao enviado: a rota chamada direto (testes, outros modulos)
    # recebe o proprio Form("[]") como valor padrao.
    if not isinstance(texto, str):
        texto = "[]"
    try:
        valor = json.loads(texto or "[]")
    except json.JSONDecodeError:
        valor = None
    if not isinstance(valor, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{campo} deve ser uma lista JSON.",
        )
    return valor


def ler_ignorados(texto: str) -> set[str]:
    """Ids de achados desmarcados (texto curto, sem dado pessoal)."""
    ids = _lista_json(texto, "ignorar")
    if len(ids) > MAX_IGNORADOS or not all(isinstance(i, str) and 0 < len(i) <= 40 for i in ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lista de achados desmarcados invalida.")
    return set(ids)


def ler_trechos(texto: str) -> list[str]:
    """Trechos acrescentados, sem repeticao, na ordem em que vieram."""
    trechos = _lista_json(texto, "trechos_extras")
    if len(trechos) > MAX_TRECHOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No maximo {MAX_TRECHOS} trechos acrescentados por documento.",
        )
    limpos: list[str] = []
    for trecho in trechos:
        if not isinstance(trecho, str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trecho acrescentado invalido.")
        trecho = " ".join(trecho.split())
        if not TAMANHO_MIN_TRECHO <= len(trecho) <= TAMANHO_MAX_TRECHO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cada trecho acrescentado precisa ter de {TAMANHO_MIN_TRECHO} a {TAMANHO_MAX_TRECHO} caracteres.",
            )
        if trecho not in limpos:
            limpos.append(trecho)
    return limpos


def detalhe_da_revisao(desmarcados: int, acrescentados: int, nao_encontrados: int) -> str:
    """Texto do evento de auditoria: so contagens, nunca o dado ou o trecho."""
    return f"desmarcados={desmarcados}; acrescentados={acrescentados}; nao_encontrados={nao_encontrados}"
