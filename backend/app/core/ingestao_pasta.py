"""Ingestao automatica da pasta base (watch de documentos).

O administrador aponta `pasta_base` no service.yaml; o servico monitora a
pasta e ingere automaticamente todo PDF que cair la: valida o conteudo,
evita duplicidade por hash e manda para a mesma fila de scan dos uploads
manuais. O original e COPIADO para o storage do servico; o arquivo na pasta
base segue sob o controle da empresa (incluido de apagar quando quiser).

O polling por hash e o mecanismo garantido: shares de rede perdem eventos
com frequencia, entao uma varredura periodica completa vira o padrao (um
event-driven watchdog acelera a reacao depois, porem e redundante).

Fluxo por arquivo: validar magic bytes/limite -> hash -> Documento
`AGUARDANDO` na equipe padrao -> fila -> scan -> auditoria
(`upload_documento` com detalhe `watch_`). Emitir documento novo nao toca
outro fluxo: quem pede documento segue por niveis como sempre.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.audit import ACAO_UPLOAD, registrar
from app.core.config import MAX_UPLOAD_BYTES, PDF_MAGIC
from app.models import Documento, Equipe, Usuario, UsuarioEquipe

logger = logging.getLogger(__name__)

STATUS_AGUARDANDO = "AGUARDANDO"
DETAHE_WATCH_PREFIXO = "watch_"


def hash_de_arquivo(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def valida_blob_pdf(conteudo: bytes) -> str | None:
    """Motivo de recusa ou None se e um PDF aceito.

    Mesmo criterio da rota de upload (nao vazio, magic bytes,
    dentro do limite de tamanho).
    """
    if not conteudo:
        return "Arquivo vazio."
    if len(conteudo) > MAX_UPLOAD_BYTES:
        return f"Arquivo excede o limite de {MAX_UPLOAD_BYTES / 1024 / 1024:.0f} MB."
    if not conteudo.startswith(PDF_MAGIC):
        return "Extensao .pdf mas conteudo nao e PDF."
    return None


class IngestorPasta:
    """Estado entre ciclos: quem recebe os documentos e como agendar o scan.

    `vinculo` (UsuarioEquipe) e o dono da ingestao: o admin da instalacao na
    equipe padrao. `agendar` pluga a fila de scan (injecao para testes).
    """

    def __init__(self, dir_base: Path, vinculo: UsuarioEquipe, agendar=None):
        if not dir_base.is_dir():
            raise ValueError(f"pasta_base nao existe: {dir_base}")
        self.dir_base = dir_base
        self.vinculo = vinculo
        self.agendar = agendar
        self._avisos: dict[str, str] = {}

    # --- ciclo ------------------------------------------------------------

    def ciclo(self, db: Session, request=None) -> int:
        """Uma varredura completa. Devolve quantos documentos foram criados."""
        criados = 0
        for caminho in sorted(self.dir_base.rglob("*.pdf")):
            if not caminho.is_file():
                continue
            if self._ingestar(db, caminho, request):
                criados += 1
        return criados

    def _ingestar(self, db: Session, caminho: Path, request=None) -> Documento | None:
        try:
            conteudo = caminho.read_bytes()
        except OSError as exc:
            self._avisar_ignorado(caminho, f"ilegivel ({exc})")
            return None

        motivo = valida_blob_pdf(conteudo)
        if motivo:
            self._avisar_ignorado(caminho, motivo)
            return None

        hash_documento = hash_de_arquivo(conteudo)
        if self._ja_conhecido(db, hash_documento):
            return None  # duplicado: silencioso, e o comportamento esperado

        documento = Documento(
            user_team_id=self.vinculo.user_team_id,
            nome_original=caminho.stem,
            extensao=caminho.suffix.lstrip(".").lower(),
            tamanho_bytes=len(conteudo),
            nivel_seguranca=1,
            chave_criptografica=hash_documento,
            hash_documento=hash_documento,
            caminho_storage="",
            status_processamento=STATUS_AGUARDANDO,
        )
        db.add(documento)
        db.flush()

        self._gravar_original(hash_documento, caminho.suffix, conteudo)
        db.commit()
        db.refresh(documento)

        registrar(
            db, request, self.vinculo.user_id, ACAO_UPLOAD,
            documento=documento, detalhe=f"{DETAHE_WATCH_PREFIXO}{STATUS_AGUARDANDO.lower()}",
        )

        if self.agendar:
            try:
                self.agendar(documento.doc_id)
            except Exception:  # noqa: BLE001 - falha de agendamento e log, nao quebra o ciclo
                logger.exception("Falha ao agendar scan do documento %s", documento.doc_id)

        logger.info("Ingerido da pasta: %s -> doc_id=%s", caminho.name, documento.doc_id)
        return documento

    # --- apoio ------------------------------------------------------------

    def _ja_conhecido(self, db: Session, hash_documento: str) -> bool:
        """Hash ja ingerido nesta instalacao.

        `ativo=False` tambem conta: re-copiar um documento arquivado seria
        ressuscita-lo por baixo do admin, sem que ele peca.
        """
        return (
            db.query(Documento)
            .filter(Documento.hash_documento == hash_documento)
            .first()
            is not None
        )

    def _gravar_original(self, hash_documento: str, extensao: str, conteudo: bytes) -> None:
        from app.core import cifra
        from app.routes.documentos import ORIGINAIS_DIR

        # O original vai CRIPTOGRAFADO para o armazenamento (Fase 3.1): o
        # scan na fila materializa a copia legivel e a descarta.
        cifra.gravar_original_cifrado(
            ORIGINAIS_DIR / f"{hash_documento}{extensao}", conteudo
        )

    def _avisar_ignorado(self, caminho: Path, motivo: str) -> None:
        # Mesmo arquivo ignora uma vez so: um share com 200 .docx nao pode
        # gerar 200 avisos por ciclo (log vira spam e ninguem le mais).
        dica = f"{caminho.name}: {motivo}"
        if self._avisos.get(caminho.name) != dica:
            self._avisos[caminho.name] = dica
            logger.warning("Arquivo ignorado da pasta base %s", dica)


class ServicoWatch:
    """Loop de leitura da pasta em thread de fundo.

    Roda um ciclo a cada `intervalo` segundos usando sessao do `sessionmaker`
    (a thread sobrevive a fim de requisicoes HTTP). `iniciar`/`parar` sao os
    ganchos de boot do servico.
    """

    def __init__(self, ingestor: IngestorPasta, sessionmaker, intervalo: int = 10):
        self.ingestor = ingestor
        self.sessionmaker = sessionmaker
        self.intervalo = max(1, intervalo)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._rodar, name="safemask-watch", daemon=True
        )
        self._thread.start()
        logger.info(
            "Watch da pasta iniciado: %s (intervalo=%ss)",
            self.ingestor.dir_base, self.intervalo,
        )

    def parar(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _rodar(self) -> None:
        while not self._stop.is_set():
            try:
                db = self.sessionmaker()
                try:
                    self.ingestor.ciclo(db)
                finally:
                    db.close()
            except Exception:  # noqa: BLE001 - o watch nunca derruba o servico
                logger.exception("Ciclo do watch falhou")
            self._stop.wait(self.intervalo)


def resolver_vinculo_ingestao(
    db: Session, nome_equipe_padrao: str
) -> tuple[UsuarioEquipe | None, str]:
    """Vinculo (usuario, equipe) que recebera os documentos da pasta base.

    Da equipe com o nome configurado (`service.yaml: equipe_padrao`),
    preferindo o vinculo de lider; se nao existir, o vinculo mais antigo.
    Instalacoes sem nenhum vinculo precisam registrar ao menos um usuario antes
    de ligar o watch (devolvemos None com o motivo para o log do boot).
    """
    equipe = (
        db.query(Equipe)
        .filter(Equipe.nome == nome_equipe_padrao)
        .first()
    )
    vinculo = None
    if equipe:
        vinculo = (
            db.query(UsuarioEquipe)
            .join(Usuario, Usuario.user_id == UsuarioEquipe.user_id)
            .filter(UsuarioEquipe.team_id == equipe.team_id)
            .order_by(UsuarioEquipe.cargo_id.desc(), UsuarioEquipe.user_team_id)
            .first()
        )
        if vinculo:
            return vinculo, f"equipe padrao '{equipe.nome}'"

    vinculo_fallback = (
        db.query(UsuarioEquipe)
        .join(Usuario, Usuario.user_id == UsuarioEquipe.user_id)
        .order_by(UsuarioEquipe.user_team_id)
        .first()
    )
    if vinculo_fallback:
        return vinculo_fallback, "equipe do primeiro usuario cadastrado"

    return None, "nenhum usuario com equipe no banco"
