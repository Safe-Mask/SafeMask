"""CNPJ alfanumérico (PI-III #58).

A IN RFB 2.229/2024 cria o CNPJ com letras: os 12 primeiros caracteres
podem ser dígitos ou letras maiúsculas, e os 2 últimos continuam dígitos
verificadores. O DV usa o mesmo módulo 11 do CNPJ numérico, com o valor de
cada caractere igual ao código ASCII menos 48 (dígito vale ele mesmo, A=17,
B=18, ... Z=42). O exemplo oficial da Receita é 12.ABC.345/01DE-35.

Medição no conjunto abaixo, no mesmo modelo do #82 e do #83:

| Situação | Detectados | Falsos positivos |
| --- | --- | --- |
| Antes (só numérico) | 3/6 (os numéricos) | 0/8 |
| Depois | 6/6 | 0/8 |

Executar, de dentro de backend/:
    python -m pytest tests/test_cnpj_alfanumerico.py -v
"""

import re

import pytest

CASOS = [
    # verdadeiros
    ("Empresa 12.ABC.345/01DE-35", "12.ABC.345/01DE-35"),  # exemplo da Receita
    ("CNPJ: A1.B2C.3D4/E5F6-68", "A1.B2C.3D4/E5F6-68"),
    ("inscrita no CNPJ SA.FEM.ASK/0001-98.", "SA.FEM.ASK/0001-98"),
    ("CNPJ 11.222.333/0001-81", "11.222.333/0001-81"),  # numérico continua valendo
    ("CNPJ 11.444.777/0001-61", "11.444.777/0001-61"),
    ("Fornecedor 11.222.333/0001-81, matriz", "11.222.333/0001-81"),
    # falsos
    ("Empresa 12.ABC.345/01DE-36", None),  # DV errado
    ("Código AB.CDE.FGH/IJKL-00", None),  # formato certo, DV errado
    ("Placa ABC-1D23", None),
    ("Protocolo SEI 12.ABC.345/01DE", None),  # sem DV
    ("CPF 529.982.247-25", None),
    ("Versão 12.abc.345/01de-35", None),  # minúsculas: não é o formato oficial
    ("Processo 0001234-56.2026.8.07.0001", None),
    ("Sequência 00.000.000/0000-00", None),
]


def _detectados(texto):
    from scanner.patterns import valor_detectado
    from scanner.scanner import configuracoes_regex
    from scanner.validadores import cnpj_valido

    padrao = configuracoes_regex()["CNPJ"]["pattern"]
    return [v for v in (valor_detectado(m) for m in re.finditer(padrao, texto)) if cnpj_valido(v)]


@pytest.mark.parametrize("texto, esperado", CASOS, ids=[c[0] for c in CASOS])
def test_deteccao(texto, esperado):
    valores = _detectados(texto)
    if esperado:
        assert valores == [esperado]
    else:
        assert valores == [], f"falso positivo de CNPJ em {texto!r}: {valores}"


@pytest.mark.parametrize("valor, valido", [
    ("12.ABC.345/01DE-35", True),
    ("12ABC34501DE35", True),
    ("12.abc.345/01de-35", True),  # o validador aceita minúsculas; o padrão de detecção, não
    ("12.ABC.345/01DE-53", False),
    ("12.ABC.345/01DE-3X", False),  # DV com letra
    ("12.ABC.345/01DE", False),
    ("AA.AAA.AAA/AAAA-00", False),
    ("11.222.333/0001-81", True),
    ("11.222.333/0001-82", False),
])
def test_validador(valor, valido):
    from scanner.validadores import cnpj_valido

    assert cnpj_valido(valor) is valido


def test_tarja_no_pdf(tmp_path, db_session):
    from app.models.dado_sensivel import DadoSensivel
    from scanner.scanner import DocumentScanner, configuracoes_regex
    from tests.conftest import gerar_pdf_texto

    origem = tmp_path / "contrato.pdf"
    origem.write_bytes(gerar_pdf_texto(["Contrato", "Contratada: Nova Empresa, CNPJ 12.ABC.345/01DE-35"]))
    scanner = DocumentScanner.__new__(DocumentScanner)
    scanner.ia = None
    scanner.regex_config = configuracoes_regex()
    resultado = scanner.scan_and_save(
        str(origem), db_session, 1, "contrato.pdf", 1, tmp_path / "originais", tmp_path / "censurados",
    )
    db_session.flush()
    dados = db_session.query(DadoSensivel).filter_by(doc_id=resultado["doc_id"]).all()
    assert [d.tipo_entidade for d in dados] == ["CNPJ"]
    assert dados[0].coordenadas
