"""Pasta de arquivos configuravel e arquivo localizado pelo nome.

Antes, `uploads/` era relativo ao diretorio de execucao, e a rota do arquivo
censurado montava o caminho com Path.cwd(): com a API iniciada fora de
backend/, os documentos "sumiam". Agora a pasta vem de SAFEMASK_PASTA_UPLOADS
(padrao backend/uploads, resolvido pelo codigo) e o arquivo e procurado pelo
nome dentro dela.
Correcao trazida do PI-III (CAMPUSCEUB/SafeMask#24).
"""

from pathlib import Path

import pytest

from app.core import armazenamento
from app.core.security import criar_token_jwt
from tests.conftest import CONTEUDO_CENSURADO


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email, 'nome': usuario.nome})}"}


def test_sem_variavel_a_pasta_e_backend_uploads(monkeypatch):
    monkeypatch.delenv(armazenamento.VARIAVEL_PASTA, raising=False)

    assert armazenamento.pasta_uploads() == armazenamento.BACKEND_DIR / "uploads"


def test_caminho_absoluto_na_variavel_e_usado_como_esta(monkeypatch, tmp_path):
    monkeypatch.setenv(armazenamento.VARIAVEL_PASTA, str(tmp_path / "dados"))

    assert armazenamento.pasta_uploads() == (tmp_path / "dados").resolve()


def test_caminho_relativo_parte_de_backend_e_nao_do_diretorio_atual(monkeypatch, tmp_path):
    monkeypatch.setenv(armazenamento.VARIAVEL_PASTA, "dados/arquivos")
    monkeypatch.chdir(tmp_path)

    assert armazenamento.pasta_uploads() == (armazenamento.BACKEND_DIR / "dados" / "arquivos").resolve()


def test_preparar_cria_as_subpastas(tmp_path):
    originais, censurados = armazenamento.preparar(tmp_path / "base")

    assert originais.is_dir() and censurados.is_dir()
    assert (originais.name, censurados.name) == ("originais", "censurados")


@pytest.mark.parametrize("gravado", [
    "uploads/censurados/abc_tarjado.pdf",
    "uploads\\censurados\\abc_tarjado.pdf",
    "/var/antigo/censurados/abc_tarjado.pdf",
    "C:\\SafeMask\\backend\\uploads\\censurados\\abc_tarjado.pdf",
])
def test_nome_do_arquivo_com_barra_do_windows_ou_do_linux(gravado):
    assert armazenamento.nome_do_arquivo(gravado) == "abc_tarjado.pdf"


def _documento_com_arquivo(seed, documento, tmp_path, caminho_gravado):
    db = seed["db"]
    doc = documento(seed["user_team_a"], hash_documento="abc", caminho_storage=caminho_gravado)
    db.add(doc)
    db.commit()
    (tmp_path / "censurados" / "abc_tarjado.pdf").write_bytes(CONTEUDO_CENSURADO)
    return doc


@pytest.mark.parametrize("caminho_gravado", [
    "uploads/censurados/abc_tarjado.pdf",
    "uploads\\censurados\\abc_tarjado.pdf",
    "/pasta/que/nao/existe/mais/censurados/abc_tarjado.pdf",
])
def test_registro_antigo_abre_pelo_nome_dentro_da_pasta(client, seed, documento, tmp_path, caminho_gravado):
    doc = _documento_com_arquivo(seed, documento, tmp_path, caminho_gravado)

    resp = client.get(f"/documentos/censurados/{doc.doc_id}/arquivo", headers=_auth(seed["usuario"]))

    assert resp.status_code == 200, resp.text
    assert resp.content == CONTEUDO_CENSURADO


def test_arquivo_abre_com_a_api_iniciada_em_outro_diretorio(
    client, seed, documento, tmp_path, monkeypatch
):
    doc = _documento_com_arquivo(seed, documento, tmp_path, "uploads/censurados/abc_tarjado.pdf")
    outro = tmp_path / "outro-diretorio"
    outro.mkdir()
    monkeypatch.chdir(outro)

    resp = client.get(f"/documentos/censurados/{doc.doc_id}/arquivo", headers=_auth(seed["usuario"]))

    assert resp.status_code == 200, resp.text


def test_arquivo_que_nao_existe_continua_404(client, seed, documento):
    db = seed["db"]
    doc = documento(seed["user_team_a"], hash_documento="sem-arquivo",
                    caminho_storage="uploads/censurados/sem-arquivo_tarjado.pdf")
    db.add(doc)
    db.commit()

    resp = client.get(f"/documentos/censurados/{doc.doc_id}/arquivo", headers=_auth(seed["usuario"]))

    assert resp.status_code == 404
    assert Path(doc.caminho_storage).name == "sem-arquivo_tarjado.pdf"
