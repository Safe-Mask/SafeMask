"""Gera PDFs de exemplo para valiar SafeMask (regex e NER).

Saidas (por padrao em /tmp/safemask-demo/):
  - relatorio_medico.pdf  : PDF com camada de texto (deteccao por regex + NER)
  - receita_escaneada.pdf : PDF so-imagem, sem texto (forca o caminho de OCR)

O PDF de texto e escrito na mao (sem lib de geracao de PDF): pdfplumber so
precisa da camada de texto no stream, e assim o arquivo e deterministico.
"""

import argparse
from pathlib import Path

# (x, y, texto) em pontos, pagina A4 (612 x 792). Cada segredo fica em uma
# linha propria para o `page.search()` do pdfplumber encontrar sem cortar.
LINHAS_RELATORIO = [
    (72, 740, "RELATORIO MEDICO - HOSPITAL SANTA CASA DE SAO PAULO"),
    (72, 712, "Paciente: Joao Carlos da Silva"),
    (72, 684, "CPF: 123.456.789-00   RG: 12345678-SSP"),
    (72, 656, "Nascimento: 15/03/1985   CNS: 123456789012345"),
    (72, 628, "Endereco: Rua das Flores, 123 - Sao Paulo/SP   CEP: 01310-100"),
    (72, 600, "Contato: joao.silva@email.com   Telefone: (11) 98765-4321"),
    (72, 572, "Medico responsavel: CRM-SP 45210"),
    (72, 544, "Diagnostico CID-10: J18.9 - Pneumonia nao especificada"),
    (72, 516, "Valor da consulta: R$ 350,00"),
    (72, 488, "Processo do convenio: 0001234-56.2026.8.26.0100"),
    (72, 460, "Clinica responsavel: Centro Medico Nova Vida"),
    (72, 432, "Atendente: Maria Fernanda Ribeiro"),
]


def _pdf_com_texto(linhas: list[tuple[float, float, str]]) -> bytes:
    """Minimal PDF de 1 pagina com texto Helvetica (sem libs externas)."""
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
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
    offsets: list[int] = []
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


def _pdf_somente_imagem(texto: str) -> bytes:
    """Renderiza o texto em uma imagem e empacota como PDF sem camada de texto.

    Sem texto extraivel o scanner cai no OCR (pytesseract, lang=por).
    """
    from PIL import Image, ImageDraw, ImageFont

    largura, altura = 1240, 1754  # ~A4 a 150 dpi
    img = Image.new("RGB", (largura, altura), "white")
    draw = ImageDraw.Draw(img)
    try:
        fonte = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except OSError:
        fonte = ImageFont.load_default()
    y = 80
    for linha in texto.splitlines():
        draw.text((80, y), linha, fill="black", font=fonte)
        y += 56
    img.save(_DESTINO_TMP / "_receita_scan.png", format="PNG")  # so p/ inspecao
    import io

    saida = io.BytesIO()
    img.convert("RGB").save(saida, format="PDF", resolution=150.0)
    saida.seek(0)
    return saida.read()


_DESTINO_TMP = Path("/tmp/safemask-demo")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=(_DESTINO_TMP / ".." / "safemask-demo"))
    args = parser.parse_args()
    destino = args.out
    destino.mkdir(parents=True, exist_ok=True)

    relatorio = destino / "relatorio_medico.pdf"
    relatorio.write_bytes(_pdf_com_texto(LINHAS_RELATORIO))

    texto_scan = (
        "RECEITA MEDICA\n"
        "Paciente: Joao Carlos da Silva\n"
        "CPF: 123.456.789-00\n"
        "Prescricao: Amoxicilina 500mg - 1 caixa\n"
    )
    receita = destino / "receita_escaneada.pdf"
    receita.write_bytes(_pdf_somente_imagem(texto_scan))

    print(f"Gerados:\n  {relatorio}\n  {receita}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())