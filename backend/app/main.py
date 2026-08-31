from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware

from app.routes import auth, dashboard, equipes, documentos
from app.database import engine, Base, SessionLocal, garantir_schema_equipes, garantir_indices
from app.models.cargo import Cargo

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
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
garantir_indices()
seed_cargos()

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(equipes.router)
app.include_router(documentos.router)

@app.get("/")
def home():
    return{"status": "online", "mensagem": "Bem vindo a API"}

    # ggg #
