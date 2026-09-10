from PIL import Image, ImageDraw


CPF_MASK = "***.***.***-**"


def draw_structured_mask(
    image: Image.Image,
    bounds: tuple[float, float, float, float],
    mask: str,
) -> None:
    left, top, right, bottom = (round(value) for value in bounds)
    drawer = ImageDraw.Draw(image)
    drawer.rectangle((left, top, right, bottom), fill="white")

    text_bounds = drawer.textbbox((0, 0), mask)
    text_width = text_bounds[2] - text_bounds[0]
    text_height = text_bounds[3] - text_bounds[1]
    text_left = left + max(2, ((right - left) - text_width) // 2)
    text_top = top + max(0, ((bottom - top) - text_height) // 2)
    drawer.text((text_left, text_top), mask, fill="black")


def draw_cpf_mask(image: Image.Image, bounds: tuple[float, float, float, float]) -> None:
    draw_structured_mask(image, bounds, CPF_MASK)
