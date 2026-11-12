"""Comprovante de anonimizacao do documento (PI-III #217).

Registro do tratamento feito em cada documento (LGPD, art. 6o, X,
responsabilizacao): tipos de dado tarjados e quantidade, paginas, ajustes
da revisao (#208), quem enviou, equipe, datas, hash e nivel de seguranca.

Nunca entra dado pessoal DO DOCUMENTO: so contagens e metadados. O PDF e
montado aqui mesmo, em memoria, com a fonte Helvetica embutida no leitor de
PDF (codificacao WinAnsi, que tem os acentos do portugues), sem dependencia
nova e sem arquivo em disco.
"""

from datetime import UTC, datetime

LARGURA, ALTURA = 595, 842  # A4 em pontos
MARGEM = 56
ROTULOS_NIVEL = {1: "Básico", 2: "Proteção média", 3: "Proteção alta", 4: "Proteção máxima"}


def _escapar(texto: str) -> bytes:
    bruto = str(texto).encode("cp1252", errors="replace")
    return bruto.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _quebrar(texto: str, limite: int) -> list[str]:
    """Quebra o texto em linhas de ate `limite` caracteres (hash longo inclusive)."""
    linhas, atual = [], ""
    for palavra in str(texto).split(" "):
        while len(palavra) > limite:
            if atual:
                linhas.append(atual)
                atual = ""
            linhas.append(palavra[:limite])
            palavra = palavra[limite:]
        candidato = f"{atual} {palavra}".strip()
        if len(candidato) > limite:
            linhas.append(atual)
            atual = palavra
        else:
            atual = candidato
    if atual:
        linhas.append(atual)
    return linhas or [""]


def gerar_pdf(titulo: str, secoes: list[tuple[str, list[str]]], rodape: str) -> bytes:
    """PDF de texto simples: titulo, secoes (subtitulo + linhas) e rodape.

    Pagina nova quando o texto passa do fim da folha.
    """
    paginas: list[list[bytes]] = [[]]
    y = ALTURA - MARGEM

    def escrever(texto: str, tamanho: int, negrito: bool = False, recuo: int = 0):
        nonlocal y
        limite = 88 if tamanho <= 10 else 70
        for linha in _quebrar(texto, limite - recuo // 6):
            if y < MARGEM + 30:
                paginas.append([])
                y = ALTURA - MARGEM
            fonte = b"/F2" if negrito else b"/F1"
            paginas[-1].append(
                b"BT " + fonte + b" %d Tf %d %d Td (" % (tamanho, MARGEM + recuo, y) + _escapar(linha) + b") Tj ET"
            )
            y -= tamanho + 5

    escrever(titulo, 16, negrito=True)
    y -= 8
    for subtitulo, linhas in secoes:
        y -= 6
        escrever(subtitulo, 12, negrito=True)
        for linha in linhas:
            escrever(linha, 10, recuo=12)

    objetos: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # Pages, preenchido abaixo
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    kids = []
    total = len(paginas)
    for numero, comandos in enumerate(paginas, start=1):
        rodape_pagina = f"{rodape} - página {numero} de {total}"
        comandos = comandos + [b"BT /F1 8 Tf %d %d Td (" % (MARGEM, MARGEM - 20) + _escapar(rodape_pagina) + b") Tj ET"]
        conteudo = b"\n".join(comandos)
        objetos.append(b"<< /Length %d >>\nstream\n" % len(conteudo) + conteudo + b"\nendstream")
        id_conteudo = len(objetos)
        objetos.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Contents %d 0 R "
            b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>" % (LARGURA, ALTURA, id_conteudo)
        )
        kids.append(b"%d 0 R" % len(objetos))
    objetos[1] = b"<< /Type /Pages /Kids [" + b" ".join(kids) + b"] /Count %d >>" % total

    saida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posicoes = []
    for numero, objeto in enumerate(objetos, start=1):
        posicoes.append(len(saida))
        saida += b"%d 0 obj\n" % numero + objeto + b"\nendobj\n"
    inicio_xref = len(saida)
    saida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for posicao in posicoes:
        saida += b"%010d 00000 n \n" % posicao
    saida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, inicio_xref)
    return bytes(saida)


def _data(valor) -> str:
    if valor is None:
        return "-"
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=UTC)
    return valor.astimezone(UTC).strftime("%d/%m/%Y %H:%M UTC")


def montar(documento, *, equipe_nome, autor_nome, contagens, ajustes, gerado_por, rotulos) -> bytes:
    """PDF do comprovante.

    `contagens`: lista de (tipo, quantidade_de_tarjas, paginas) vinda de
    dado_sensivel. `ajustes`: detalhe do evento `revisar_tarjas` ou None.
    """
    nivel = ROTULOS_NIVEL.get(documento.nivel_seguranca, str(documento.nivel_seguranca))
    if contagens:
        tarjas = [
            f"{rotulos.get(tipo, tipo)}: {quantidade} tarja(s), página(s) {', '.join(str(p + 1) for p in paginas)}"
            for tipo, quantidade, paginas in contagens
        ]
        total = sum(q for _, q, _ in contagens)
        tarjas.append(f"Total: {total} tarja(s) de {len(contagens)} tipo(s) de dado.")
    else:
        tarjas = ["Nenhum dado pessoal foi detectado ou marcado neste documento."]

    original = "Guardado no servidor; só o cargo com permissão para o original o abre."

    secoes = [
        ("Documento", [
            f"Título: {documento.nome_original}",
            f"Identificador: #{documento.doc_id}",
            f"Equipe: {equipe_nome or '-'}",
            f"Enviado por: {autor_nome or '-'}",
            f"Data do envio: {_data(documento.criado_em)}",
            f"Nível de segurança: {nivel}",
            f"Hash SHA-256 do original: {documento.hash_documento}",
        ]),
        ("Dados protegidos com tarja", tarjas),
        ("Revisão antes de salvar", [
            f"Ajustes registrados: {ajustes}" if ajustes else "Nenhum ajuste: as tarjas são as da detecção automática.",
        ]),
        ("Documento original", [original]),
        ("Sobre este comprovante", [
            "Registra o tratamento feito no documento (LGPD, art. 6º, X). Não contém nenhum dado pessoal "
            "do documento: só tipos, quantidades, páginas e metadados.",
            "O hash permite conferir que o original é o mesmo arquivo enviado.",
        ]),
    ]
    gerado = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
    return gerar_pdf(
        "Comprovante de anonimização - SafeMask",
        secoes,
        f"Gerado em {gerado} por {gerado_por}",
    )
