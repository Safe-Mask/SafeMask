"""Testes unitários dos validadores de CPF e CNPJ.

Não dependem de banco, PDF nem do scanner: exercitam apenas a aritmética
do dígito verificador e as regras de rejeição.

Executar, de dentro de backend/:
    python -m pytest tests/test_validadores.py -v
"""

import pytest

from scanner.validadores import (
    VALIDADORES,
    apenas_digitos,
    cnpj_valido,
    cpf_valido,
    sequencia_repetida,
)

# ----------------------------------------------------------------- helpers

class TestApenasDigitos:
    def test_remove_pontos_traco_e_barra(self):
        assert apenas_digitos("529.982.247-25") == "52998224725"
        assert apenas_digitos("11.222.333/0001-81") == "11222333000181"

    def test_mantem_string_so_de_digitos(self):
        assert apenas_digitos("52998224725") == "52998224725"

    def test_vazio_e_none(self):
        assert apenas_digitos("") == ""
        assert apenas_digitos(None) == ""


class TestSequenciaRepetida:
    @pytest.mark.parametrize("valor", ["11111111111", "00000000000000", "9"])
    def test_detecta_repetida(self, valor):
        assert sequencia_repetida(valor) is True

    @pytest.mark.parametrize("valor", ["52998224725", "11222333000181", ""])
    def test_nao_repetida(self, valor):
        assert sequencia_repetida(valor) is False


# --------------------------------------------------------------------- CPF

class TestCpfValido:
    @pytest.mark.parametrize("cpf", [
        "529.982.247-25",
        "111.444.777-35",
        "52998224725",       # sem formatação
        "111444777 35",      # separador incomum: só os dígitos importam
        "123.456.789-09",    # parece exemplo inventado, mas os dígitos verificadores batem
    ])
    def test_aceita_cpf_com_digitos_corretos(self, cpf):
        assert cpf_valido(cpf) is True

    @pytest.mark.parametrize("cpf", [
        "529.982.247-24",    # último dígito errado
        "529.982.247-15",    # penúltimo dígito errado
        "123.456.789-00",    # formato certo, dígitos errados
    ])
    def test_rejeita_digito_verificador_incorreto(self, cpf):
        assert cpf_valido(cpf) is False

    @pytest.mark.parametrize("cpf", [
        "111.111.111-11",
        "000.000.000-00",
        "999.999.999-99",
    ])
    def test_rejeita_sequencia_repetida(self, cpf):
        assert cpf_valido(cpf) is False

    @pytest.mark.parametrize("cpf", [
        "529.982.247",       # 9 dígitos
        "529.982.247-2",     # 10 dígitos
        "529.982.247-255",   # 12 dígitos
        "",
        None,
    ])
    def test_rejeita_tamanho_incorreto(self, cpf):
        assert cpf_valido(cpf) is False


# -------------------------------------------------------------------- CNPJ

class TestCnpjValido:
    @pytest.mark.parametrize("cnpj", [
        "11.222.333/0001-81",
        "11.444.777/0001-61",
        "11222333000181",    # sem formatação
    ])
    def test_aceita_cnpj_com_digitos_corretos(self, cnpj):
        assert cnpj_valido(cnpj) is True

    @pytest.mark.parametrize("cnpj", [
        "11.222.333/0001-82",   # último dígito errado
        "11.222.333/0001-71",   # penúltimo dígito errado
        "12.345.678/0001-00",   # formato certo, dígitos errados
    ])
    def test_rejeita_digito_verificador_incorreto(self, cnpj):
        assert cnpj_valido(cnpj) is False

    @pytest.mark.parametrize("cnpj", [
        "00.000.000/0000-00",
        "11.111.111/1111-11",
    ])
    def test_rejeita_sequencia_repetida(self, cnpj):
        assert cnpj_valido(cnpj) is False

    @pytest.mark.parametrize("cnpj", [
        "11.222.333/0001",      # 12 dígitos
        "11.222.333/0001-8",    # 13 dígitos
        "",
        None,
    ])
    def test_rejeita_tamanho_incorreto(self, cnpj):
        assert cnpj_valido(cnpj) is False


# -------------------------------------------------------- mapa do scanner

class TestMapaValidadores:
    def test_cobre_exatamente_cpf_e_cnpj(self):
        assert set(VALIDADORES) == {"CPF", "CNPJ"}

    def test_funcoes_corretas(self):
        assert VALIDADORES["CPF"] is cpf_valido
        assert VALIDADORES["CNPJ"] is cnpj_valido
