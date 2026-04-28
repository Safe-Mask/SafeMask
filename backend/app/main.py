from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware

from app.routes import auth, dashboard, equipes, documentos
from app.database import engine, Base, garantir_schema_equipes

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

Base.metadata.create_all(bind=engine)
garantir_schema_equipes()

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(equipes.router)
app.include_router(documentos.router)

@app.get("/")
def home():
    return{"status": "online", "mensagem": "Bem vindo a API"}
