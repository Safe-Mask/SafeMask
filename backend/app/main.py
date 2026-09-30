import logging

from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS, descrever
from app.core.http_headers import HeadersSegurancaMiddleware
from app.database import (
    Base,
    SessionLocal,
    engine,
    garantir_indices,
    garantir_schema_documentos,
    garantir_schema_equipes,
    garantir_schema_organizacoes,
)
from app.models.cargo import Cargo
from app.routes import auth, dashboard, documentos, equipes

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
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
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
# Antes de garantir_indices(): os indices de tenant so podem ser criados
# depois que as colunas organizacao_id existirem.
garantir_schema_organizacoes()
garantir_indices()
seed_cargos()

logger.info("Configuracao ativa: %s", descrever())

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(equipes.router)
app.include_router(documentos.router)

@app.get("/")
def home():
    return{"status": "online", "mensagem": "Bem vindo a API"}
