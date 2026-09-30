"""Coordenadas de mascaramento: um so espaco, uma so verdade.

Uma pagina lida por texto entrega pontos do PDF (pdfplumber). Uma pagina que
so tem imagem passa por OCR, que entrega pixels da imagem renderizada a 150
dpi. As duas coisas estao em `DadoSensivel.coordenadas`, sem distinciao: a
descensura parcial recebia pixels, chamava `_reproject` (que espera pontos) e a
tarja saia deslocada — em documento escaneado a tarja protectoria nao cobria
o dado, e o pior: cobria outra coisa.

Este modulo guarda a distincao e a conversao.
"""

# Espaco das coordenadas salvas. `pdf` = pontos do PDF (72/pt), `pixel` =
# pixels da imagem renderizada em RESOLUCAO_RENDERIZACAO dpi.
ESPACO_PDF = "pdf"
ESPACO_PIXEL = "pixel"

RESOLUCAO_RENDERIZACAO = 150

# 72 pontos por polegada e a base do PDF; com isso, um pixel da imagem
# renderizada vale 72/RESOLUCAO_RENDERIZACAO pontos.
PONTOS_POR_PIXEL = 72.0 / RESOLUCAO_RENDERIZACAO

_MARGEM_PIXEL = 2


def para_pontos(coordenadas, espaco: str) -> list:
    """Coordenadas no espaco do PDF, vindo de `espaco`.

    `pdf` devolve a lista como esta. `pixel` converte pela resolucao usada na
    renderizacao.
    """
    x0, y0, x1, y1 = _quatro(coordenadas)
    if espaco == ESPACO_PDF:
        return [x0, y0, x1, y1]
    if espaco == ESPACO_PIXEL:
        return [v / RESOLUCAO_RENDERIZACAO * 72.0 for v in (x0, y0, x1, y1)]
    raise ValueError(f"Espaco de coordenadas desconhecido: {espaco!r}")


def para_pixels(coordenadas, espaco: str) -> list:
    """Coordenadas em pixels da imagem renderizada, vindo de `espaco`."""
    x0, y0, x1, y1 = _quatro(coordenadas)
    if espaco == ESPACO_PIXEL:
        return [x0, y0, x1, y1]
    if espaco == ESPACO_PDF:
        return [v / 72.0 * RESOLUCAO_RENDERIZACAO for v in (x0, y0, x1, y1)]
    raise ValueError(f"Espaco de coordenadas desconhecido: {espaco!r}")


def _quatro(coordenadas) -> tuple:
    valores = list(coordenadas)
    if len(valores) != 4:
        raise ValueError(
            f"Coordenada deve ter 4 valores (x0, y0, x1, y1); veio {len(valores)}."
        )
    if any(v is None for v in valores):
        raise ValueError("Coordenada com valor nulo.")
    return tuple(float(v) for v in valores)


def normalizar(coordenadas, espaco: str, largura: float, altura: float) -> list | None:
    """Caixa utilizavel dentro da pagina, ou None se nao der para cobrir.

    Descarta o que nao daria para(mask|tar)ar de qualquer jeito:
      - coordenadas invertidas (x1 < x0): trocou a ordem;
      - largura ou altura zero: caixa degenerada, nao cobre nada;
      - caixa fora da pagina inteira: a pagina nao existe ali.

    Uma caixa que *atravessa* a borda e recortada, nao descartada: um dado na
    margem de uma pagina escaneada gera caixa levemente maior que a pagina e
    ainda precisa de tarja.
    """
    try:
        x0, y0, x1, y1 = para_pontos(coordenadas, espaco)
    except ValueError:
        return None

    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0

    if (x1 - x0) <= 0 or (y1 - y0) <= 0:
        return None

    # Dente minimo: uma tarja de menos de 1 ponto e um ponto de tinta.
    largura_min, altura_min = 1.0, 1.0

    x0, y0 = max(x0, 0.0), max(y0, 0.0)
    x1, y1 = min(x1, largura), min(y1, altura)

    if (x1 - x0) < largura_min or (y1 - y0) < altura_min:
        return None
    if x1 <= x0 or y1 <= y0:
        return None

    return [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]


def tem_cobertura_util(coordenadas, espaco: str) -> bool:
    """A caixa tem area, em qualquer espaco? Checagem barata antes de desenhar."""
    try:
        x0, y0, x1, y1 = _quatro(coordenadas)
    except ValueError:
        return False
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return (x1 - x0) > 0 and (y1 - y0) > 0


def apenas_irrelevante(coordenadas, espaco: str) -> bool:
    """Alias legivel para quem valida listas: a caixa nao serve para nada."""
    return not tem_cobertura_util(coordenadas, espaco)


def aplicar_margem(coordenadas, espaco: str, margem: int = _MARGEM_PIXEL) -> list:
    """Alarga a caixa no espaco indicado, para a tarja pegar a borda do glifo."""
    fator = PONTOS_POR_PIXEL if espaco == ESPACO_PIXEL else 1.0
    x0, y0, x1, y1 = _quatro(coordenadas)
    return [x0 - margem * fator, y0 - margem * fator, x1 + margem * fator, y1 + margem * fator]
