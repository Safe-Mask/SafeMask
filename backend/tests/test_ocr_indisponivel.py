"""PDF escaneado sem OCR disponivel.

Pagina sem texto vai para o OCR (Tesseract). Sem o Tesseract, ou sem o idioma
portugues, o upload respondia 500 "Erro ao processar documento." sem dizer o
motivo. Agora responde 503 com uma mensagem clara e nao grava documento.
Trazido do PI-III (CAMPUSCEUB/SafeMask#172).
"""

import io

import pytesseract
import pytest
from PIL import Image

from app.core.security import criar_token_jwt
from app.models.documentos import Documento

AUTH = {"Authorization": f"Bearer {criar_token_jwt({'sub': 'ana@safemask.example.com', 'nome': 'Ana'})}"}


def _pdf_escaneado() -> bytes:
    """Uma pagina so de imagem: nenhum texto extraivel."""
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), "white").save(buf, "PDF")
    return buf.getvalue()


@pytest.fixture
def scanner_real(monkeypatch):
    from app.routes import documentos as documentos_routes
    from scanner.scanner import DocumentScanner, configuracoes_regex

    scanner = DocumentScanner.__new__(DocumentScanner)
    scanner.ia = None
    scanner.regex_config = configuracoes_regex()
    monkeypatch.setattr(documentos_routes, "get_scanner", lambda: scanner)
    return scanner


@pytest.mark.parametrize("erro, trecho", [
    (pytesseract.TesseractNotFoundError(), "não está instalado"),
    (pytesseract.TesseractError(1, "Failed loading language 'por'"), "português"),
])
def test_upload_escaneado_sem_ocr_tem_mensagem_clara(client, seed, scanner_real, monkeypatch, erro, trecho):
    from scanner import scanner as modulo_scanner

    def sem_ocr(*args, **kwargs):
        raise erro

    monkeypatch.setattr(modulo_scanner.pytesseract, "image_to_string", sem_ocr)
    antes = seed["db"].query(Documento).count()

    resp = client.post(
        "/documentos/upload",
        headers=AUTH,
        files={"file": ("oficio.pdf", _pdf_escaneado(), "application/pdf")},
        data={"titulo": "Oficio", "nivel_seguranca": "1", "teams": f"[{seed['equipe_a'].team_id}]"},
    )

    assert resp.status_code == 503, resp.text
    assert "escaneado" in resp.json()["detail"]
    assert trecho in resp.json()["detail"]
    assert seed["db"].query(Documento).filter(Documento.status_processamento != "ERRO").count() == antes


def test_caminho_do_tesseract_vem_da_variavel_de_ambiente(monkeypatch, tmp_path):
    from scanner import scanner as modulo_scanner

    executavel = tmp_path / "tesseract.exe"
    executavel.write_bytes(b"")
    monkeypatch.setenv("TESSERACT_CMD", str(executavel))
    monkeypatch.setattr(modulo_scanner.pytesseract.pytesseract, "tesseract_cmd", "tesseract")

    modulo_scanner.configurar_tesseract()

    assert modulo_scanner.pytesseract.pytesseract.tesseract_cmd == str(executavel)
