"""O PDF censurado salvo pelo scan precisa conter as tarjas.

Regressao: `_desenhar_caixa_pil` pinta as caixas em `img_pagina.original` do
pdfplumber, mas o `_scan` montava o PDF de saida a partir de
`img_pagina.annotated` — uma copia do raster tirada por `to_image()` ANTES de
pintar. O resultado era um "PDF tarjado" que nao tapa nada em paginas com
camada de texto, e o documento mais importante da demo (relatorio com CPF)
saia com o dado legivel.
"""

from PIL import Image

from scanner.scanner import DocumentScanner, configuracoes_regex


def _pdf_com_cpf() -> bytes:
    """Minimal PDF A4 com titulo e CPF (mesma tecnica do gerador de exemplo)."""
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
    ]
    linhas = [
        (72, 760, "RELATORIO MEDICO - TESTE SAFEMASK"),
        (72, 730, "CPF: 123.456.789-00"),
        (72, 700, "CEP: 01310-100"),
    ]
    bt = ["BT /F1 11 Tf"]
    for x, y, texto in linhas:
        esc = texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        bt.append(f"1 0 0 1 {x} {y} Tm ({esc}) Tj")
    bt.append("ET")
    conteudo = "\n".join(bt).encode("latin-1", "replace")
    objetos.append(
        b"<< /Length " + str(len(conteudo)).encode() + b" >>\nstream\n"
        + conteudo + b"\nendstream"
    )
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, obj in enumerate(objetos, start=1):
        offsets.append(len(buf))
        buf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_pos = len(buf)
    n = len(objetos) + 1
    buf += f"xref\n0 {n}\n".encode()
    buf += b"0000000000 65535 f \n"
    for off in offsets:
        buf += f"{off:010d} 00000 n \n".encode()
    buf += (
        f"trailer\n<< /Size {n} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return bytes(buf)


def _renderizar(pdf_path, escala):
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    return pdf[0].render(scale=escala).to_pil().convert("RGB")


def _fracao_escura(img: Image.Image, x0, top, x1, bottom, escala) -> float:
    """Proporcao de pixels escuros na caixa, com coords em pontos do PDF."""
    px0, ptop = int(x0 * escala), int(top * escala)
    px1, pbot = int(x1 * escala), int(bottom * escala)
    px0, ptop = max(0, px0), max(0, ptop)
    px1, pbot = min(img.width, max(px0 + 2, px1)), min(img.height, max(ptop + 2, pbot))
    regiao = img.crop((px0, ptop, px1, pbot)).convert("L")
    dados = list(regiao.getdata())
    return sum(1 for v in dados if v < 100) / len(dados)


def _caixa_do(pdf_path, segredo):
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        res = pdf.pages[0].search(segredo)
        assert res, f"pdfplumber nao encontrou '{segredo}' no PDF de teste"
        r = res[0]
        return r["x0"], r["top"], r["x1"], r["bottom"]


def test_pdf_censurado_contem_as_tarjas(tmp_path, db_session):
    origem = tmp_path / "relatorio_teste.pdf"
    origem.write_bytes(_pdf_com_cpf())

    scanner = DocumentScanner.__new__(DocumentScanner)
    scanner.ia = None
    scanner.regex_config = configuracoes_regex()

    dir_original = tmp_path / "originais"
    dir_censurado = tmp_path / "censurados"
    resultado = scanner.scan_and_save(
        str(origem), db_session, 1, "relatorio_teste.pdf", 1,
        dir_original, dir_censurado,
    )

    assert resultado["status"] == "CONCLUIDO"
    tarjados = list(dir_censurado.glob("*_tarjado.pdf"))
    assert tarjados == [dir_censurado / resultado["caminho_censurado"].split("/")[-1]]

    escala = 150 / 72  # scanner renderiza a 150 dpi; px por ponto do PDF
    rend_origem = _renderizar(origem, escala)
    rend_tarjado = _renderizar(tarjados[0], 1.0)

    for segredo, rotulo in (("123.456.789-00", "CPF"), ("01310-100", "CEP")):
        caixa = _caixa_do(origem, segredo)
        fracao_origem = _fracao_escura(rend_origem, *caixa, escala=escala)
        fracao_tarjado = _fracao_escura(rend_tarjado, *caixa, escala=escala)

        assert fracao_tarjado > fracao_origem + 0.15, (
            f"a tarja nao apareceu no PDF salvo: {rotulo}"
            f" origem={fracao_origem:.2f} tarjado={fracao_tarjado:.2f}"
        )
