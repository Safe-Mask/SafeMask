"""Politica de niveis por equipe.

Cada tipo de dado detectado tem um nivel exigido para ser revelado na
descensura parcial (membro 1, supervisor 2, lider 3). O padrao e o nivel de
`configuracoes_regex()`; o lider de cada equipe pode ajusta-lo, e o upload
aplica a politica da equipe de destino. A mudanca vale para os documentos
enviados depois dela: os ja processados mantem o nivel gravado em
`dado_sensivel`, que e o que a descensura consulta.
"""

from sqlalchemy.orm import Session

from app.models.politica_nivel import PoliticaNivel
from scanner.scanner import configuracoes_regex

NIVEIS_PADRAO = {tipo: int(config["level"]) for tipo, config in configuracoes_regex().items()}

ROTULOS = {
    "CPF": "CPF",
    "RG": "RG",
    "CNS": "Cartão Nacional de Saúde (CNS)",
    "CID10": "CID-10 (diagnóstico)",
    "CRM": "CRM (registro médico)",
    "EMAIL": "E-mail",
    "TELEFONE": "Telefone",
    "DATA_NASC": "Data de nascimento",
    "CNPJ": "CNPJ",
    "PROCESSO": "Número de processo",
    "ENDERECO": "CEP",
}

NIVEL_MINIMO = 1
NIVEL_MAXIMO = 3


class PoliticaInvalida(ValueError):
    """Tipo de dado desconhecido ou nivel fora de 1 a 3."""


def niveis_da_equipe(db: Session, team_id: int) -> dict[str, int]:
    """Nivel exigido de cada tipo para a equipe: o padrao, com os ajustes dela."""
    niveis = dict(NIVEIS_PADRAO)
    for linha in db.query(PoliticaNivel).filter(PoliticaNivel.team_id == team_id).all():
        if linha.tipo_entidade in niveis:
            niveis[linha.tipo_entidade] = linha.nivel_requerido
    return niveis


def validar(niveis: dict) -> dict[str, int]:
    """Normaliza os tipos (maiusculas) e confere tipo e nivel de cada um."""
    if not niveis:
        raise PoliticaInvalida("Informe o nível de ao menos um tipo de dado.")

    normalizados = {}
    for tipo, nivel in niveis.items():
        chave = str(tipo).strip().upper()
        if chave not in NIVEIS_PADRAO:
            raise PoliticaInvalida(f"Tipo de dado desconhecido: {tipo}.")
        if isinstance(nivel, bool) or not isinstance(nivel, int) or not NIVEL_MINIMO <= nivel <= NIVEL_MAXIMO:
            raise PoliticaInvalida(
                f"O nível de {ROTULOS.get(chave, chave)} deve ser de {NIVEL_MINIMO} a {NIVEL_MAXIMO}."
            )
        normalizados[chave] = nivel
    return normalizados


def definir(db: Session, team_id: int, niveis: dict[str, int]) -> None:
    """Grava os niveis ja validados. Quem chama faz o commit.

    So o que difere do padrao vira linha: voltar um tipo ao padrao apaga o
    ajuste, e a equipe passa a acompanhar o padrao dali em diante.
    """
    existentes = {
        linha.tipo_entidade: linha
        for linha in db.query(PoliticaNivel).filter(PoliticaNivel.team_id == team_id).all()
    }
    for tipo, nivel in niveis.items():
        linha = existentes.get(tipo)
        if nivel == NIVEIS_PADRAO[tipo]:
            if linha is not None:
                db.delete(linha)
        elif linha is not None:
            linha.nivel_requerido = nivel
        else:
            db.add(PoliticaNivel(team_id=team_id, tipo_entidade=tipo, nivel_requerido=nivel))


def descrever(niveis: dict[str, int]) -> list[dict]:
    """Linhas da tela: tipo, rotulo, nivel atual e o padrao."""
    return [
        {"tipo": tipo, "rotulo": ROTULOS.get(tipo, tipo), "nivel": niveis[tipo], "padrao": padrao}
        for tipo, padrao in NIVEIS_PADRAO.items()
    ]
