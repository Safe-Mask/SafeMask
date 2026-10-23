import logging

from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

from app.core import fila, seed_instalacao, service_config
from app.core.config import CORS_ORIGIN_REGEX, CORS_ORIGINS, descrever
from app.core.http_headers import HeadersSegurancaMiddleware
from app.core.troca_senha import MiddlewareTrocaSenhaObrigatoria
from app.database import (
    Base,
    SessionLocal,
    corrigir_extensao_documentos,
    engine,
    garantir_indices,
    garantir_schema_auditoria,
    garantir_schema_documentos,
    garantir_schema_equipes,
    garantir_schema_organizacoes,
)
from app.models.cargo import Cargo
from app.routes import auditoria, auth, dashboard, documentos, equipes

logger = logging.getLogger(__name__)

middleware = [
    # Headers primeiro: assim valem tambem para as respostas JSON e para os
    # arquivos, sem depender de cada rota lembrar de aplica-los.
    Middleware(HeadersSegurancaMiddleware),
    Middleware(
        CORSMiddleware,
        # Lista explicita: com allow_credentials=True, "*" faria o navegador
        # descartar o header e a API responder sem Access-Control-Allow-Origin.
        allow_origins=CORS_ORIGINS,
        allow_origin_regex=CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        # Sem isso o navegador esconde o nome do arquivo nos downloads feitos
        # por fetch (ex.: exportacao da auditoria em CSV).
        expose_headers=["Content-Disposition"],
    ),
    # Ultimo na cadeia: so recusa quem tem troca de senha pendente (admin do
    # 1o boot), depois de CORS resolver o preflight.
    Middleware(MiddlewareTrocaSenhaObrigatoria),
]

app = FastAPI(
    title="API",
    description="API para SafeMask",
    version="0.1.0",
    middleware=middleware
)

def seed_cargos():
    """Garante que os cargos minimos existam no banco (lider/supervisor/membro)."""
    db = SessionLocal()
    try:
        for nome, nivel, descricao in [
            ("lider", 3, "Gerencia equipe, define cargos e adiciona membros"),
            ("supervisor", 2, "Pode adicionar membros à equipe"),
            ("membro", 1, "Apenas visualiza documentos"),
        ]:
            existe = db.query(Cargo).filter(Cargo.nome == nome).first()
            if not existe:
                db.add(Cargo(nome=nome, nivel=nivel, descricao=descricao))
        db.commit()
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
garantir_schema_equipes()
garantir_schema_documentos()
corrigir_extensao_documentos()
# Antes de garantir_indices(): os indices de tenant so podem ser criados
# depois que as colunas organizacao_id existirem.
garantir_schema_organizacoes()
# Colunas de contexto e indices da trilha de auditoria.
garantir_schema_auditoria()
garantir_indices()
seed_cargos()

# Configuracao de instalacao: pasta base, porta e equipe padrao da empresa
# (service.yaml ao lado do exe). Nada quebrado no boot quando o arquivo
# falta ou tem valor invalido.
CONFIG = service_config.carregar()
logger.info("Configuracao do servico: %s", CONFIG.descritor())

# Instalacao nova: organiza unica + admin + equipe padrao (idempotente).
seed_instalacao.semear(SessionLocal())

_watch = None


def ligar_watch() -> None:
    """Sobe o watch da pasta base, quando configurado e com dono valido."""
    global _watch
    if not CONFIG.pasta_base:
        logger.info("Pasta base nao configurada; watch desligado")
        return

    from app.core.ingestao_pasta import IngestorPasta, ServicoWatch, resolver_vinculo_ingestao
    from app.routes.documentos import processar_upload_da_fila

    db = SessionLocal()
    try:
        vinculo, motivo = resolver_vinculo_ingestao(db, CONFIG.equipe_padrao)
    finally:
        db.close()
    if vinculo is None:
        logger.warning("Watch desligado: %s", motivo)
        return

    def agendar_scan(doc_id: int) -> None:
        fila.agendar(processar_upload_da_fila, doc_id)

    _watch = ServicoWatch(
        IngestorPasta(CONFIG.pasta_base.expanduser(), vinculo, agendar=agendar_scan),
        SessionLocal,
        CONFIG.intervalo_watch,
    )
    _watch.iniciar()


ligar_watch()

logger.info("Configuracao ativa: %s", descrever())

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(equipes.router)
app.include_router(documentos.router)
app.include_router(auditoria.router)

@app.get("/")
def home():
    return{"status": "online", "mensagem": "Bem vindo a API"}


@app.on_event("shutdown")
def desligar_servico():
    """Nenhuma tarefa de scan/watch fica pela metade na hora do desligamento."""
    if _watch is not None:
        _watch.parar()
    fila.desligar()
