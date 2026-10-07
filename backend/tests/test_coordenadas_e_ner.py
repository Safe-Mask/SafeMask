"""Coordenadas de mascaramento e mapa de entidades do NER (Fatia 6).

O ponto central: `DadoSensivel.coordenadas` misturava dois espacos. Pagina com
texto devolve pontos do PDF; pagina escaneada devolve pixels da imagem a 150
dpi. A descensura parcial tratava pixels como pontos, a tarja saia deslocada e
o dado ficava visivel — falha silenciosa que so aparecia em documento
escaneado.
"""

import pytest

from scanner.coordenadas import (
    ESPACO_PDF,
    ESPACO_PIXEL,
    PONTOS_POR_PIXEL,
    RESOLUCAO_RENDERIZACAO,
    normalizar,
    para_pixels,
    para_pontos,
    tem_cobertura_util,
)
from scanner.scanner import (
    ENTIDADES_DESCARTADAS,
    MAPA_ENTIDADES_NER,
    DocumentScanner,
    _desempacotar_caixa,
    entidades_saidas_do_modelo,
    entidades_sem_mapa,
)


def _niveis_do_regex() -> dict:
    """`{tipo: nivel}` do `configuracoes_regex()`, sem carregar o modelo NER."""
    from scanner.scanner import configuracoes_regex

    return {tipo: cfg["level"] for tipo, cfg in configuracoes_regex().items()}


# --- conversao entre espacos -------------------------------------------------


def test_pixel_vira_ponto_pela_resolucao():
    """150 dpi -> 1 pixel vale 72/150 pontos."""
    pontos = para_pontos([150, 300, 450, 600], ESPACO_PIXEL)
    assert pontos == pytest.approx([
        150 * PONTOS_POR_PIXEL, 300 * PONTOS_POR_PIXEL,
        450 * PONTOS_POR_PIXEL, 600 * PONTOS_POR_PIXEL,
    ])


def test_pdf_vira_pixel_pela_resolucao():
    """O caminho inverso."""
    pixels = para_pixels([72, 72, 144, 144], ESPACO_PDF)
    assert pixels == pytest.approx([
        72 / 72 * RESOLUCAO_RENDERIZACAO, 72 / 72 * RESOLUCAO_RENDERIZACAO,
        144 / 72 * RESOLUCAO_RENDERIZACAO, 144 / 72 * RESOLUCAO_RENDERIZACAO,
    ])


def test_ida_e_volta_preserva_a_caixa():
    original = [150.0, 300.0, 450.0, 600.0]
    volta = para_pixels(para_pontos(original, ESPACO_PIXEL), ESPACO_PDF)
    assert volta == pytest.approx(original)


def test_espaco_desconhecido_falha_barulhento():
    with pytest.raises(ValueError):
        para_pontos([0, 0, 10, 10], "polegada")


def test_coordenada_com_numero_errado_de_valores_falha():
    with pytest.raises(ValueError):
        para_pontos([0, 0, 10], ESPACO_PDF)


def test_coordenada_nula_falha():
    with pytest.raises(ValueError):
        para_pontos([0, 0, 10, None], ESPACO_PDF)


# --- validacao / normalizacao ------------------------------------------------


def test_caixa_valida_passa_inalterada():
    assert normalizar([10, 20, 100, 60], ESPACO_PDF, 595, 842) == [10, 20, 100, 60]


def test_caixa_invertida_e_arrumada():
    """x1 menor que x0 nao e erro do scan: e so ordem trocada."""
    assert normalizar([100, 60, 10, 20], ESPACO_PDF, 595, 842) == [10, 20, 100, 60]


def test_caixa_de_area_zero_e_descartada():
    """Largura zero nao cobre nada."""
    assert normalizar([10, 20, 10, 60], ESPACO_PDF, 595, 842) is None


def test_caixa_de_altura_zero_e_descartada():
    assert normalizar([10, 20, 100, 20], ESPACO_PDF, 595, 842) is None


def test_caixa_totalmente_fora_da_pagina_e_descartada():
    assert normalizar([700, 900, 800, 1000], ESPACO_PDF, 595, 842) is None


def test_caixa_que_atravessa_a_borda_e_recortada_nao_descartada():
    """Um dado na margem gera caixa maior que a pagina e ainda precisa de tarja."""
    util = normalizar([560, 800, 700, 900], ESPACO_PDF, 595, 842)
    assert util is not None
    assert util[0] == 560 and util[2] == 595
    assert util[1] == 800 and util[3] == 842


def test_caixa_normalizada_de_pixel_e_recortada_em_pontos():
    """Pixel passa a ponto ANTES do recorte, senao o limite esta na unidade errada."""
    largura_px = 595 * RESOLUCAO_RENDERIZACAO / 72
    altura_px = 842 * RESOLUCAO_RENDERIZACAO / 72
    util = normalizar(
        [largura_px - 10, altura_px - 10, largura_px + 100, altura_px + 100],
        ESPACO_PIXEL, 595, 842,
    )
    assert util is not None
    assert util[2] <= 595 and util[3] <= 842


def test_tem_cobertura_util_detecta_degenerada():
    assert tem_cobertura_util([10, 20, 100, 60], ESPACO_PDF)
    assert not tem_cobertura_util([10, 20, 10, 60], ESPACO_PDF)
    assert not tem_cobertura_util([10, 20, 100, 20], ESPACO_PDF)


# --- desempacotamento do que a rota monta ------------------------------------


def test_desempacota_forma_nova():
    assert _desempacotar_caixa(([1, 2, 3, 4], ESPACO_PIXEL)) == ([1, 2, 3, 4], ESPACO_PIXEL)


def test_desempacota_forma_antiga_como_pdf():
    """Dados gravados antes da coluna existirem sao pontos do PDF."""
    assert _desempacotar_caixa([1, 2, 3, 4]) == ([1, 2, 3, 4], ESPACO_PDF)


# --- mapa de entidades do NER ------------------------------------------------


def test_modelo_real_nao_tem_entidade_sem_regra():
    """A regressao que motivou a Fatia 6: 14 entidades treinadas eram jogadas fora.

    CNH, CEP, PLACA_VEICULO, JURISPRUDENCIA, TEMPO, VALOR e EVENTO nao tem
    regex que as cubra — sem o mapa, elas nunca eram censuradas.
    """
    sem_mapa = entidades_sem_mapa()
    assert sem_mapa == set(), (
        f"Entidade(s) do modelo sem regra: {sorted(sem_mapa)}"
    )


def test_entidades_criticas_do_modelo_estao_mapeadas():
    saidas = entidades_saidas_do_modelo()
    for critico in ("CPF", "CNH", "CEP", "PLACA_VEICULO", "RG", "DATA_NASCIMENTO"):
        assert critico in saidas, f"{critico} nao e emitido pelo modelo?"
        assert critico in MAPA_ENTIDADES_NER, f"{critico} nao esta no mapa"


def test_nivel_do_ner_bate_com_o_do_regex():
    """O mesmo dado nao pode ter dois niveis, senao a descensura depende de
    qual detector viu primeiro.

    Os niveis do regex sao lidos do proprio `regex_config`, sem duplicar o
    numero no teste: se alguem mudar o regex, este teste acusa.
    """
    from scanner.scanner import DocumentScanner

    levels = _niveis_do_regex()
    paridade = {
        "CPF": "CPF", "CNPJ": "CNPJ", "EMAIL": "EMAIL", "TELEFONE": "TELEFONE",
        "RG": "RG", "DATA_NASCIMENTO": "DATA_NASC", "NUMERO_PROCESSO": "PROCESSO",
    }
    for entidade_ner, tipo_regex in paridade.items():
        nivel_ner, tipo_ner = MAPA_ENTIDADES_NER[entidade_ner]
        assert tipo_ner == tipo_regex, (
            f"{entidade_ner}: NER grava como {tipo_ner}, regex como {tipo_regex}"
        )
        assert tipo_regex in levels, f"regex removedido do teste: {tipo_regex}"
        assert nivel_ner == levels[tipo_regex], (
            f"{entidade_ner}: NER diz nivel {nivel_ner}, regex diz {levels[tipo_regex]}"
        )


def test_niveis_do_regex_sao_os_niveis_documentados():
    """Trava a escala que o resto do sistema assume (1 supervisor, 3 lider)."""
    assert _niveis_do_regex() == {
        "CPF": 3, "CNPJ": 1, "EMAIL": 2, "TELEFONE": 2, "CNS": 3,
        "CID10": 3, "CRM": 3, "RG": 3, "PROCESSO": 1, "DATA_NASC": 2,
        "ENDERECO": 1,
    }


def test_entidade_descartada_exige_motivacao_escrita():
    """Descartar entidade sem motivo e o bug que some documento da tela."""
    assert ENTIDADES_DESCARTADAS, "esperado ao menos o rotulo vazio do tokenizer"
    for rotulo, motivo in ENTIDADES_DESCARTADAS.items():
        assert motivo.strip(), f"'{rotulo}' descartada sem motivo"


# --- contagem de dados salvos ---------------------------------------------


def _scanner_sem_modelo() -> DocumentScanner:
    """Instancia sem __init__: os testes aqui nao devem carregar o NER."""
    return DocumentScanner.__new__(DocumentScanner)


class _PaginaStub:
    """Simula a pagina do pdfplumber: largura, altura e `search()`."""

    width = 595.0
    height = 842.0

    def __init__(self, resultado):
        self._resultado = resultado

    def search(self, _termo):
        return self._resultado


def test_salvar_dado_conta_cada_caixa_persistida(db_session):
    """`salvos` precisa somar as caixas gravadas, nao ficar preso em zero.

    Regressao do commit ca859a3: o incremento foi perdido quando o corpo
    migrou para `_salvar_caixa`, e `total_sensiveis`/`cpf_censurados`
    voltavam sempre 0 na resposta do upload.
    """
    scanner = _scanner_sem_modelo()
    pagina = _PaginaStub([
        {"x0": 10, "top": 20, "x1": 100, "bottom": 60},
        {"x0": 200, "top": 300, "x1": 320, "bottom": 340},
    ])

    salvos, coordenadas = scanner._salvar_dado(
        db_session, 1, pagina, 0, "123.456.789-00", "CPF", 3
    )

    assert salvos == 2
    assert len(coordenadas) == 2


def test_salvar_dado_nao_conta_caixa_degenerada(db_session):
    """Caixa sem cobertura nao vai para o banco e nao conta como salva."""
    scanner = _scanner_sem_modelo()
    pagina = _PaginaStub([{"x0": 10, "top": 20, "x1": 10, "bottom": 60}])

    salvos, coordenadas = scanner._salvar_dado(
        db_session, 1, pagina, 0, "123.456.789-00", "CPF", 3
    )

    assert salvos == 0
    assert coordenadas == []


def test_salvar_dado_conta_caixas_do_ocr(db_session):
    """No caminho de OCR, cada palavra do segredo vira uma caixa contada."""
    scanner = _scanner_sem_modelo()
    pagina = _PaginaStub([])
    ocr_data = {
        "text": ["CPF", "123.456.789-00", "e", "nome"],
        "left": [10, 50, 0, 0], "top": [20, 30, 0, 0],
        "width": [30, 120, 0, 0], "height": [15, 15, 0, 0],
    }

    salvos, coordenadas = scanner._salvar_dado(
        db_session, 1, pagina, 0, "123.456.789-00", "CPF", 3,
        usando_ocr=True, ocr_data=ocr_data,
    )

    assert salvos == 1
    assert len(coordenadas) == 1
