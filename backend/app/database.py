import logging
import os
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("safemask.slow_query")

load_dotenv()

# DATABASE_URL = (
#    f"postgresql+psycopg2://"
#    f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
#    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
#    f"/{os.getenv('DB_NAME')}"
#---)

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

# Importa todos os models para que fiquem registrados em Base.metadata antes
# de create_all(). Precisa ficar depois de `Base = declarative_base()`.
from app.models import *  # noqa: E402,F403
from app.models.organizacao import Organizacao  # noqa: E402


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
        "CREATE INDEX IF NOT EXISTS idx_equipe_organizacao_id ON equipe(organizacao_id)",
        "CREATE INDEX IF NOT EXISTS idx_usuario_organizacao_id ON usuario(organizacao_id)",
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


def garantir_schema_documentos():
    inspector = inspect(engine)
    if "documentos" not in inspector.get_table_names():
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns("documentos")}
    if "cpf_censurados" in colunas:
        return

    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE documentos "
                    "ADD COLUMN IF NOT EXISTS cpf_censurados INTEGER NOT NULL DEFAULT 0"
                )
            )
        elif engine.dialect.name == "sqlite":
            conn.execute(
                text(
                    "ALTER TABLE documentos "
                    "ADD COLUMN cpf_censurados INTEGER NOT NULL DEFAULT 0"
                )
            )


def _ddl_adicionar_organizacao(dialecto: str) -> dict[str, str]:
    """DDL de `ALTER TABLE` por tabela, ajustado ao dialeto.

    Postgres aceita `ADD COLUMN IF NOT EXISTS`, o que torna a migracao
    segura para rodar em paralelo. SQLite (usado nos testes) nao aceita e
    falha a sentenca; la o filtro de colunas ja garante que nao repetimos.
    """
    ddl = {
        "usuario": "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS organizacao_id INTEGER",
        "equipe": "ALTER TABLE equipe ADD COLUMN IF NOT EXISTS organizacao_id INTEGER",
    }
    if dialecto == "sqlite":
        return {tabela: sql.replace("IF NOT EXISTS ", "") for tabela, sql in ddl.items()}
    return ddl


def _ddl_adicionar_coluna_espaco(dialecto: str) -> str:
    """DDL da coluna que diz em que espaco estao as coordenadas.

    Coluna nova com `DEFAULT 'pdf'` e `NOT NULL`: as linhas que ja existem
    materialmente cidram em `pdf`, que era o unico espaco que o scanner usava
    antes dela existir. Sem o default, o `ALTER TABLE` falharia em banco com
    dado.
    """
    sql = (
        "ALTER TABLE dado_sensivel ADD COLUMN IF NOT EXISTS "
        "espaco_coordenadas VARCHAR(10) NOT NULL DEFAULT 'pdf'"
    )
    if dialecto == "sqlite":
        return sql.replace("IF NOT EXISTS ", "")
    return sql


def garantir_schema_organizacoes():
    """Cria as colunas de tenant e alinha os dados ja existentes.

    `criar_telas()` roda antes e cria a tabela `organizacao`. Aqui so
    acrescentamos `organizacao_id` em `usuario` e `equipe`, que em bancos
    existentes nao tem a coluna.

    Os registros sem organizacao vao para uma unica organizacao legada. Criar
    uma organizacao por equipe mudaria quem enxerga o que, e essa decisao e de
    negocio; enquanto ela nao for tomada, o comportamento atual e preservado.
    """
    inspector = inspect(engine)
    tabelas = set(inspector.get_table_names())

    # `criar_telas()` normalmente ja criou a tabela no boot, mas criar aqui
    # deixa a migracao autocontida e executavel isoladamente.
    Organizacao.__table__.create(bind=engine, checkfirst=True)
    tabelas.add("organizacao")

    alteracoes = _ddl_adicionar_organizacao(engine.dialect.name)

    pendentes = {}
    for tabela, ddl in alteracoes.items():
        if tabela not in tabelas:
            continue
        colunas = {coluna["name"] for coluna in inspector.get_columns(tabela)}
        if "organizacao_id" in colunas:
            continue
        pendentes[tabela] = ddl

    with engine.begin() as conn:
        for ddl in pendentes.values():
            conn.execute(text(ddl))

    # As colunas novas vem antes do backfill: ele consulta `Usuario` pelo
    # modelo, e o modelo ja seleciona `token_version`. Sem a coluna, o proprio
    # backfill quebra com "no such column".
    _garantir_espaco_coordenadas(inspector, tabelas)
    _garantir_token_version(inspector, tabelas)

    _preencher_organizacoes_pendentes()


def _garantir_espaco_coordenadas(inspector, tabelas: set):
    """Acrescenta `dado_sensivel.espaco_coordenadas` em bancos existentes."""
    if "dado_sensivel" not in tabelas:
        return
    colunas = {c["name"] for c in inspector.get_columns("dado_sensivel")}
    if "espaco_coordenadas" in colunas:
        return
    with engine.begin() as conn:
        conn.execute(text(_ddl_adicionar_coluna_espaco(engine.dialect.name)))


def _garantir_token_version(inspector, tabelas: set):
    """Acrescenta `usuario.token_version` em bancos existentes.

    Coluna NOT NULL DEFAULT 0: todo usuario ja existente vale versao 0, que e
    exatamente o valor dos tokens de acesso ja emitidos. Sem o default o
    `ALTER TABLE` quebraria com dado em tabela.
    """
    if "usuario" not in tabelas:
        return
    colunas = {c["name"] for c in inspector.get_columns("usuario")}
    if "token_version" in colunas:
        return
    sql = (
        "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS "
        "token_version INTEGER NOT NULL DEFAULT 0"
    )
    if engine.dialect.name == "sqlite":
        sql = sql.replace("IF NOT EXISTS ", "")
    with engine.begin() as conn:
        conn.execute(text(sql))


def _preencher_organizacoes_pendentes():
    """Backfill das linhas sem organizacao, uma vez, em qualquer boot."""
    # Import local: `app.core.tenancy` importa os models, que importam este
    # modulo. Dentro da funcao o `app.database` ja esta carregado.
    from app.core.tenancy import ORGANIZACAO_LEGADA_NOME
    from app.models.equipe import Equipe
    from app.models.organizacao import Organizacao
    from app.models.usuario import Usuario

    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        pendentes = (
            db.query(Usuario).filter(Usuario.organizacao_id.is_(None)).count()
            + db.query(Equipe).filter(Equipe.organizacao_id.is_(None)).count()
        )
        if pendentes == 0:
            return

        legada = (
            db.query(Organizacao)
            .filter(Organizacao.nome == ORGANIZACAO_LEGADA_NOME)
            .order_by(Organizacao.organizacao_id)
            .first()
        )
        if not legada:
            legada = Organizacao(nome=ORGANIZACAO_LEGADA_NOME)
            db.add(legada)
            db.flush()

        atualizadas = (
            db.query(Usuario)
            .filter(Usuario.organizacao_id.is_(None))
            .update(
                {Usuario.organizacao_id: legada.organizacao_id},
                synchronize_session=False,
            )
        )
        atualizadas += (
            db.query(Equipe)
            .filter(Equipe.organizacao_id.is_(None))
            .update(
                {Equipe.organizacao_id: legada.organizacao_id},
                synchronize_session=False,
            )
        )
        db.commit()
        logger.info(
            "Organizacao legada '%s' criada; %s registros vinculados.",
            ORGANIZACAO_LEGADA_NOME,
            atualizadas,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    criar_tabelas()
