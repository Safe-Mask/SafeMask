"""Cifra do original em disco (Fase 3.1 do PLANO_DESKTOP)."""

import pytest
from cryptography.fernet import Fernet

from app.core import cifra
from app.core.security import criar_token_jwt
from tests.conftest import CONTEUDO_PDF


def _auth(usuario):
    return {"Authorization": f"Bearer {criar_token_jwt({'sub': usuario.email})}"}


def _upload_individual(client, seed, scanner_registrado):
    scanner_registrado([(3, 0)])
    return client.post(
        "/documentos/upload",
        data={
            "titulo": "Contrato",
            "nivel_seguranca": "1",
            "teams": f"[{seed['equipe_a'].team_id}]",
        },
        files={"file": ("contrato.pdf", CONTEUDO_PDF, "application/pdf")},
        headers=_auth(seed["usuario"]),
    )


def test_round_trip_e_materializacao_nao_alteram_o_original(tmp_path):
    original = tmp_path / "doc.pdf"
    cifra.gravar_original_cifrado(original, CONTEUDO_PDF)

    bruto = original.read_bytes()
    assert cifra.e_cifrado(bruto)
    assert CONTEUDO_PDF not in bruto
    assert cifra.decifrar_arquivo(original) == CONTEUDO_PDF

    legivel = cifra.materializar_original_para_leitura(original)
    assert legivel != original
    assert legivel.read_bytes() == CONTEUDO_PDF

    cifra.descartar_material_temporario(legivel, original)
    assert not legivel.exists()
    assert cifra.e_cifrado(original.read_bytes())


def test_texto_puro_legado_e_lido_sem_copia(tmp_path):
    legado = tmp_path / "antigo.pdf"
    legado.write_bytes(CONTEUDO_PDF)

    assert not cifra.e_cifrado(legado.read_bytes())
    assert cifra.decifrar_arquivo(legado) == CONTEUDO_PDF

    legivel = cifra.materializar_original_para_leitura(legado)
    assert legivel == legado
    cifra.descartar_material_temporario(legivel, legado)
    assert legado.read_bytes() == CONTEUDO_PDF


def test_chave_diferente_nao_abre_original(tmp_path, monkeypatch):
    original = tmp_path / "doc.pdf"
    cifra.gravar_original_cifrado(original, CONTEUDO_PDF)

    monkeypatch.setenv(
        "SAFEMASK_CHAVE_ARQUIVO", str(tmp_path / "outra_chave.key")
    )
    monkeypatch.setattr(cifra, "_fernet_cache", None)
    (tmp_path / "outra_chave.key").write_bytes(Fernet.generate_key())

    with pytest.raises(cifra.OrigemIlegivel):
        cifra.decifrar_arquivo(original)


def test_migracao_cifra_legado_e_idempotente(tmp_path):
    diretorio = tmp_path / "originais"
    diretorio.mkdir()
    legado = diretorio / "legado.pdf"
    legado.write_bytes(CONTEUDO_PDF)
    ja_cifrado = diretorio / "novo.pdf"
    cifra.gravar_original_cifrado(ja_cifrado, CONTEUDO_PDF)
    token_antes = ja_cifrado.read_bytes()

    migrados, falhas = cifra.migrar_originais_em_texto_puro(diretorio)

    assert (migrados, falhas) == (1, 0)
    assert cifra.e_cifrado(legado.read_bytes())
    assert cifra.decifrar_arquivo(legado) == CONTEUDO_PDF
    assert ja_cifrado.read_bytes() == token_antes

    assert cifra.migrar_originais_em_texto_puro(diretorio) == (0, 0)


def test_upload_individual_grava_original_cifrado(
    client, seed, scanner_registrado
):
    resposta = _upload_individual(client, seed, scanner_registrado)
    assert resposta.status_code == 201, resposta.text

    from app.routes import documentos as documentos_routes

    arquivos = list(documentos_routes.ORIGINAIS_DIR.iterdir())
    assert arquivos
    for arquivo in arquivos:
        bruto = arquivo.read_bytes()
        assert cifra.e_cifrado(bruto), arquivo
        assert CONTEUDO_PDF not in bruto
        assert cifra.decifrar_arquivo(arquivo) == CONTEUDO_PDF


def test_upload_lote_grava_original_cifrado(client, seed, scanner_registrado):
    scanner_registrado([(3, 0)])
    resposta = client.post(
        "/documentos/upload/lote",
        data={
            "team_id": str(seed["equipe_a"].team_id),
            "nivel_seguranca": "1",
        },
        files=[
            ("files", ("contrato.pdf", CONTEUDO_PDF, "application/pdf")),
        ],
        headers=_auth(seed["usuario"]),
    )
    assert resposta.status_code == 202, resposta.text

    from app.routes import documentos as documentos_routes

    arquivos = list(documentos_routes.ORIGINAIS_DIR.iterdir())
    assert arquivos
    for arquivo in arquivos:
        assert cifra.e_cifrado(arquivo.read_bytes()), arquivo
        assert cifra.decifrar_arquivo(arquivo) == CONTEUDO_PDF
