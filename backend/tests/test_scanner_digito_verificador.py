"""O scanner so tarja CPF com digito verificador correto.

`123.456.789-00` tem o formato de CPF, mas o digito verificador nao confere:
e numero de exemplo, nao dado pessoal. Trazido do PI-III
(CAMPUSCEUB/SafeMask#55).
"""

from scanner.scanner import DocumentScanner, configuracoes_regex
from tests.test_scan_salva_tarjas import _pdf_com_cpf


def _escanear(tmp_path, db_session, pdf: bytes):
    origem = tmp_path / "doc.pdf"
    origem.write_bytes(pdf)
    scanner = DocumentScanner.__new__(DocumentScanner)
    scanner.ia = None
    scanner.regex_config = configuracoes_regex()
    resultado = scanner.scan_and_save(
        str(origem), db_session, 1, "doc.pdf", 1, tmp_path / "originais", tmp_path / "censurados",
    )
    return resultado["cpf_censurados"]


def test_cpf_valido_e_detectado(tmp_path, db_session):
    assert _escanear(tmp_path, db_session, _pdf_com_cpf()) == 1


def test_cpf_com_digito_errado_nao_e_detectado(tmp_path, db_session):
    # Mesmo tamanho: o PDF continua valido com a troca do ultimo digito.
    pdf = _pdf_com_cpf().replace(b"123.456.789-09", b"123.456.789-00")

    assert _escanear(tmp_path, db_session, pdf) == 0
