from sqlalchemy import create_engine, inspect, text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time
import logging
from dotenv import load_dotenv

logger = logging.getLogger("safemask.slow_query")

load_dotenv()

# DATABASE_URL = (
#    f"postgresql+psycopg2://"
#    f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
#    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
#    f"/{os.getenv('DB_NAME')}"
#)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL nao configurada no arquivo .env")

# Neon normalmente fornece postgresql://...; garantimos driver psycopg2 explicito.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_SLOW_QUERY_MS = int(os.getenv("SLOW_QUERY_MS", "100"))

if _SLOW_QUERY_MS > 0:
    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("_qstart", []).append(time.monotonic())

    @event.listens_for(engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        elapsed_ms = (time.monotonic() - conn.info["_qstart"].pop()) * 1000
        if elapsed_ms >= _SLOW_QUERY_MS:
            logger.warning("SLOW QUERY %.0fms | %s", elapsed_ms, statement[:300])

Base = declarative_base()

from app.models import *

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas():
    Base.metadata.create_all(bind=engine)


def garantir_indices():
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_documentos_user_team_id ON documentos(user_team_id)",
        "CREATE INDEX IF NOT EXISTS idx_documentos_criado_em ON documentos(criado_em DESC)",
        "CREATE INDEX IF NOT EXISTS idx_dado_sensivel_doc_id ON dado_sensivel(doc_id)",
        "CREATE INDEX IF NOT EXISTS idx_usuario_equipe_team_id ON usuario_equipe(team_id)",
        "CREATE INDEX IF NOT EXISTS idx_log_auditoria_user_id ON log_auditoria(user_id)",
    ]
    with engine.begin() as conn:
        for ddl in indices:
            conn.execute(text(ddl))


def garantir_schema_equipes():
    inspector = inspect(engine)
    if "equipe" not in inspector.get_table_names():
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns("equipe")}
    if "descricao" in colunas:
        return

    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE equipe ADD COLUMN IF NOT EXISTS descricao TEXT"))
        elif engine.dialect.name == "sqlite":
            conn.execute(text("ALTER TABLE equipe ADD COLUMN descricao TEXT"))


if __name__ == "__main__":
    criar_tabelas()
