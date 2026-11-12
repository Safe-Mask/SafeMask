"""Data de nascimento pelo contexto (PI-III #178).

Depois do PI-III #177 as datas ficaram desligadas, porque o padrão antigo tarjava
qualquer dd/mm/aaaa (vigência, assinatura, publicação). Agora a data só é
data de nascimento depois de um rótulo ("data de nascimento", "nascido(a)
em", "DN:", "dt. nasc.", "nasc."), e precisa ser uma data válida. A tarja
cobre só a data. Ligado por padrão; `SAFEMASK_DETECTAR_DATAS=1` continua
religando o modo antigo, que tarja toda data.

Medição no conjunto abaixo:

| Situação | Detectados | Falsos positivos |
| --- | --- | --- |
| Antes, padrão (desligado, #177) | 0/7 | 0/9 |
| Antes, com SAFEMASK_DETECTAR_DATAS=1 | 4/7 | 6/9 |
| Depois (pelo contexto) | 7/7 | 0/9 |

Executar, de dentro de backend/:
    python -m pytest tests/test_data_nascimento.py -v
"""

import re

import pytest

from tests.conftest import gerar_pdf_texto

CASOS = [
    # verdadeiros: rótulo de nascimento + data válida
    ("Data de nascimento: 15/03/1990", "15/03/1990"),
    ("nascida em 02/07/1985, natural de Brasília", "02/07/1985"),
    ("Nascido em 5 de março de 1979", "5 de março de 1979"),
    ("DN: 31.12.2000", "31.12.2000"),
    ("Dt. Nasc.: 01-01-1950", "01-01-1950"),
    ("data de nascimento 15/03/1990.", "15/03/1990"),
    ("Nasc. 09/09/1999 - Sexo: F", "09/09/1999"),
    # falsos: datas de documento, data inválida, rótulo sem data
    ("Vigência: 01/10/2020 a 30/09/2021", None),
    ("Assinatura: 23/09/2020", None),
    ("Publicado em 10/11/2026", None),
    ("Prazo de entrega: 30/11/2026", None),
    ("Data de nascimento: 31/02/1990", None),  # 31 de fevereiro não existe
    ("Nascimento do projeto em 2020", None),
    ("nascido em Brasília, em 1990", None),
    ("Data de nascimento: 15/03/2090", None),  # no futuro
    ("Processo 0001234-56.2026.8.07.0001", None),
]


def _valores(texto):
    from scanner.patterns import valor_detectado
    from scanner.scanner import DocumentScanner
    from scanner.validadores import VALIDADORES

    config = DocumentScanner().regex_config
    if "DATA_NASC" not in config:
        return []
    validador = VALIDADORES.get("DATA_NASC")
    valores = [valor_detectado(m) for m in re.finditer(config["DATA_NASC"]["pattern"], texto)]
    return [v for v in valores if validador is None or validador(v)]


@pytest.mark.parametrize("texto, esperado", CASOS, ids=[c[0] for c in CASOS])
def test_deteccao_pelo_contexto(monkeypatch, texto, esperado):
    monkeypatch.delenv("SAFEMASK_DETECTAR_DATAS", raising=False)
    valores = _valores(texto)
    if esperado:
        assert valores == [esperado]
    else:
        assert valores == [], f"falso positivo de data de nascimento em {texto!r}: {valores}"


@pytest.mark.parametrize("valor, valida", [
    ("15/03/1990", True), ("31/02/1990", False), ("29/02/2000", True), ("29/02/1900", False),
    ("5 de março de 1979", True), ("5 de marco de 1979", True), ("32 de maio de 1990", False),
    ("01/13/1990", False), ("15/03/1890", False), ("15/03/2090", False),
])
def test_validador_de_data(valor, valida):
    from scanner.validadores import data_nascimento_valida

    assert data_nascimento_valida(valor) is valida


def test_documento_tarja_so_a_data_de_nascimento(tmp_path, db_session, monkeypatch):
    from app.models.dado_sensivel import DadoSensivel
    from scanner.scanner import DocumentScanner, configuracoes_regex

    monkeypatch.delenv("SAFEMASK_DETECTAR_DATAS", raising=False)
    origem = tmp_path / "ficha.pdf"
    origem.write_bytes(gerar_pdf_texto([
        "FICHA",
        "Data de nascimento: 15/03/1990",
        "Vigencia: 01/10/2020 a 30/09/2021. Assinatura: 23/09/2020.",
    ]))
    scanner = DocumentScanner.__new__(DocumentScanner)
    scanner.ia = None
    scanner.regex_config = configuracoes_regex()
    resultado = scanner.scan_and_save(
        str(origem), db_session, 1, "ficha.pdf", 1, tmp_path / "originais", tmp_path / "censurados",
    )
    db_session.flush()
    dados = db_session.query(DadoSensivel).filter_by(doc_id=resultado["doc_id"]).all()
    assert [d.tipo_entidade for d in dados] == ["DATA_NASC"]
    # A tarja cobre so a data: a caixa e mais estreita que o rotulo + data.
    x0, _, x1, _ = dados[0].coordenadas
    assert 40 < (x1 - x0) < 90


def test_modo_antigo_continua_disponivel(monkeypatch):
    monkeypatch.setenv("SAFEMASK_DETECTAR_DATAS", "1")
    assert _valores("Assinatura: 23/09/2020") == ["23/09/2020"]
