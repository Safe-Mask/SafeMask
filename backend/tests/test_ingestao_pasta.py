"""Watch da pasta base: ingestao automatica com dedupe por hash e fila."""

from pathlib import Path

from app.core.ingestao_pasta import (
    IngestorPasta,
    ServicoWatch,
    hash_de_arquivo,
    resolver_vinculo_ingestao,
    valida_blob_pdf,
)
from app.models import Documento, LogAuditoria
from app.models.usuario_equipe import UsuarioEquipe
from app.routes import documentos as documentos_routes
from tests.conftest import CONTEUDO_PDF


def _vinculo_do_seed(seed):
    return (
        seed["db"].query(UsuarioEquipe)
        .filter(UsuarioEquipe.user_team_id == seed["user_team_a"])
        .one()
    )


def test_valida_blob_rejeita_o_mesmo_que_a_rota():
    assert valida_blob_pdf(b"") is not None
    assert valida_blob_pdf(b"nao-e-pdf") is not None
    assert valida_blob_pdf(CONTEUDO_PDF) is None
    assert valida_blob_pdf(b"%PDF-" + b"x" * 30_000_000) is not None


def test_ciclo_ingere_pdf_novo_com_auditoria_e_fila(seed, tmp_path, monkeypatch):
    db = seed["db"]
    monkeypatch.setattr(documentos_routes, "ORIGINAIS_DIR", tmp_path / "originais")

    agendas = []
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "contrato.pdf").write_bytes(CONTEUDO_PDF)

    ingestor = IngestorPasta(inbox, _vinculo_do_seed(seed), agendar=agendas.append)
    criados = ingestor.ciclo(db)

    assert criados == 1
    documento = db.query(Documento).one()
    assert documento.status_processamento == "AGUARDANDO"
    assert documento.hash_documento == hash_de_arquivo(CONTEUDO_PDF)
    assert documento.user_team_id == seed["user_team_a"]
    assert agendas == [documento.doc_id]

    evento = db.query(LogAuditoria).filter_by(acao="upload_documento").one()
    assert evento.doc_id == documento.doc_id
    assert evento.detalhe == "watch_aguardando"


def test_dedupe_ignora_repeticao_e_descarta_nao_pdf(seed, tmp_path, monkeypatch):
    db = seed["db"]
    monkeypatch.setattr(documentos_routes, "ORIGINAIS_DIR", tmp_path / "originais")

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    ingestor = IngestorPasta(inbox, _vinculo_do_seed(seed))
    (inbox / "contrato.pdf").write_bytes(CONTEUDO_PDF)

    assert ingestor.ciclo(db) == 1
    # Re-copiar o mesmo PDF (nome diferente, mesmo conteudo) nao reingere.
    (inbox / "contrato-copia.pdf").write_bytes(CONTEUDO_PDF)
    (inbox / "notas.docx").write_bytes(b"docx ignorado")
    assert ingestor.ciclo(db) == 0
    assert db.query(Documento).count() == 1


def test_original_e_copiado_para_o_storage_do_servico(seed, tmp_path, monkeypatch):
    db = seed["db"]
    originais = tmp_path / "originais-do-servico"
    monkeypatch.setattr(documentos_routes, "ORIGINAIS_DIR", originais)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    ingestor = IngestorPasta(inbox, _vinculo_do_seed(seed))
    (inbox / "contrato.pdf").write_bytes(CONTEUDO_PDF)

    ingestor.ciclo(db)

    documento = db.query(Documento).one()
    # Antes do scan o tarjado nao existe; quem preenche `caminho_storage`
    # (com o caminho CENSURADO) e o scanner do lote.
    assert documento.caminho_storage == ""
    copiado = originais / f"{documento.hash_documento}.pdf"
    assert copiado.is_file()
    from app.core import cifra

    bruto = copiado.read_bytes()
    assert cifra.e_cifrado(bruto)
    assert cifra.decifrar_arquivo(copiado) == CONTEUDO_PDF


def test_resolver_vinculo_prefere_a_equipe_padrao_e_sabe_fallback(seed):
    db = seed["db"]

    vinculo_default, motivo = resolver_vinculo_ingestao(db, "Equipe A")
    assert vinculo_default.user_team_id == seed["user_team_a"]
    assert "Equipe A" in motivo

    fallback, motivo_fallback = resolver_vinculo_ingestao(db, "Equipe Inexistente")
    assert fallback is not None
    assert "equipe do primeiro usuario" in motivo_fallback


def test_sem_nenhum_vinculo_nao_tem_de_quem_ser_ingestor(db_session):
    vazio, motivo = resolver_vinculo_ingestao(db_session, "Equipe A")
    assert vazio is None
    assert "nenhum usuario" in motivo


def test_watch_thread_para_quando_pedem(seed, tmp_path):
    import time

    from sqlalchemy.orm import sessionmaker

    db = seed["db"]
    ingestor = IngestorPasta(tmp_path, _vinculo_do_seed(seed))
    watch = ServicoWatch(ingestor, sessionmaker(bind=db.get_bind()), intervalo=1)

    watch.iniciar()
    assert watch._thread is not None
    time.sleep(0.1)
    watch.parar()
    assert watch._thread is None
    # pasta vazia: nenhum documento criado por acidente
    assert db.query(Documento).count() == 0
