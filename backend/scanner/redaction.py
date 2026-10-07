from PIL import Image, ImageDraw, ImageFont

CPF_MASK = "***.***.***-**"


def _fonte_que_cabe(drawer: ImageDraw.ImageDraw, mask: str, box_w: int, box_h: int):
    """Maior fonte default que deixa `mask` inteira dentro da caixa.

    Sem isto os asteriscos usavam a fonte bitmap fixa do PIL e sumiam numa
    caixa de 150 dpi: a regiao ficava so branca, sem mascara visivel.
    """
    fonte = ImageFont.load_default()
    tamanho = 1
    while tamanho <= 200:
        candidata = ImageFont.load_default(size=tamanho)
        bb = drawer.textbbox((0, 0), mask, font=candidata)
        if (bb[2] - bb[0]) > box_w or (bb[3] - bb[1]) > box_h:
            break
        fonte = candidata
        tamanho += 1
    return fonte


def draw_structured_mask(
    image: Image.Image,
    bounds: tuple[float, float, float, float],
    mask: str,
) -> None:
    left, top, right, bottom = (round(value) for value in bounds)
    drawer = ImageDraw.Draw(image)
    drawer.rectangle((left, top, right, bottom), fill="black")

    box_w = max(1, right - left)
    box_h = max(1, bottom - top)
    fonte = _fonte_que_cabe(drawer, mask, box_w, box_h)
    text_bounds = drawer.textbbox((0, 0), mask, font=fonte)
    text_width = text_bounds[2] - text_bounds[0]
    text_height = text_bounds[3] - text_bounds[1]
    text_left = left + max(2, (box_w - text_width) // 2)
    text_top = top + max(0, (box_h - text_height) // 2)
    drawer.text((text_left, text_top), mask, fill="white", font=fonte)


def draw_cpf_mask(image: Image.Image, bounds: tuple[float, float, float, float]) -> None:
    draw_structured_mask(image, bounds, CPF_MASK)
