"""Deteccao de CEP, CNH e cartao de pagamento (PI-III #83).

- CEP: 00000-000, 00.000-000 ou 8 digitos depois do rotulo "CEP". Continua
  gravado como ENDERECO, o tipo que o grupo ja usava para o CEP.
- CNH: 11 digitos depois de um rotulo de habilitacao, com o DV conferido.
- Cartao: grupos 4-4-4-4 (ou 4-6-5) ou 13 a 19 digitos depois de "cartao",
  conferido pelo algoritmo de Luhn.

Medicao no conjunto de `casos_cep_cnh_cartao.py`: CEP 6/6 e 0/8 falsos
positivos, CNH 5/5 e 0/6, cartao 5/5 e 0/7.
"""

import re

import pytest

from scanner.patterns import valor_detectado
from scanner.scanner import DocumentScanner, configuracoes_regex
from scanner.validadores import VALIDADORES, cartao_valido, cnh_valida
from tests.casos_cep_cnh_cartao import CARTAO, CEP, CNH
from tests.conftest import gerar_pdf_texto


def _detectados(tipo, texto):
    padrao = configuracoes_regex()[tipo]["pattern"]
    validador = VALIDADORES.get(tipo)
    valores = [valor_detectado(m) for m in re.finditer(padrao, texto)]
    return [v for v in valores if validador is None or validador(v)]


def _conferir(tipo, texto, esperado):
    valores = _detectados(tipo, texto)
    if esperado:
        assert valores == [esperado]
    else:
        assert valores == [], f"falso positivo de {tipo} em {texto!r}: {valores}"


@pytest.mark.parametrize("texto, esperado", CEP, ids=[c[0] for c in CEP])
def test_cep(texto, esperado):
    _conferir("ENDERECO", texto, esperado)


@pytest.mark.parametrize("texto, esperado", CNH, ids=[c[0] for c in CNH])
def test_cnh(texto, esperado):
    _conferir("CNH", texto, esperado)


@pytest.mark.parametrize("texto, esperado", CARTAO, ids=[c[0] for c in CARTAO])
def test_cartao(texto, esperado):
    _conferir("CARTAO", texto, esperado)


@pytest.mark.parametrize("valor, valido", [
    ("02650306461", True), ("12345678900", True), ("04281773660", True),
    ("02650306462", False), ("98765432100", False), ("11111111111", False),
    ("0265030646", False), ("026.503.064-61", True),
])
def test_cnh_valida(valor, valido):
    assert cnh_valida(valor) is valido


@pytest.mark.parametrize("valor, valido", [
    ("4111 1111 1111 1111", True), ("5555-5555-5555-4444", True), ("378282246310005", True),
    ("4111111111111112", False), ("0000000000000000", False), ("411111111111", False),
    ("41111111111111111111", False),
])
def test_cartao_valido(valor, valido):
    assert cartao_valido(valor) is valido


def test_cnh_rotulada_nao_vira_cpf():
    """CNH e CPF tem 11 digitos: o CPF exige pontos e traco, a CNH exige rotulo."""
    assert _detectados("CPF", "CNH 02650306461") == []
    assert _detectados("CNH", "CPF 529.982.247-25") == []


def test_cep_nao_pega_trecho_de_telefone_nem_cns():
    assert _detectados("ENDERECO", "Telefone (61) 99876-5432") == []
    assert _detectados("CNH", "CNS 898001160112342") == []


def test_documento_com_os_tipos_novos_e_tarjado(tmp_path, db_session):
    from app.models.dado_sensivel import DadoSensivel

    origem = tmp_path / "ficha.pdf"
    origem.write_bytes(gerar_pdf_texto([
        "FICHA CADASTRAL FICTICIA",
        "Endereco: SQS 308 Bloco A, CEP 70355-010, Brasilia/DF",
        "CNH 02650306461, categoria B",
        "Cartao 4111 1111 1111 1111",
        "Protocolo 20261234",
    ]))
    scanner = DocumentScanner.__new__(DocumentScanner)
    scanner.ia = None
    scanner.regex_config = configuracoes_regex()
    resultado = scanner.scan_and_save(
        str(origem), db_session, 1, "ficha.pdf", 1, tmp_path / "originais", tmp_path / "censurados",
    )
    db_session.flush()
    dados = db_session.query(DadoSensivel).filter_by(doc_id=resultado["doc_id"]).all()
    assert sorted(d.tipo_entidade for d in dados) == ["CARTAO", "CNH", "ENDERECO"]
    assert all(d.coordenadas for d in dados)
    assert {d.tipo_entidade: d.nivel_requerido for d in dados} == {"CARTAO": 3, "CNH": 3, "ENDERECO": 1}
