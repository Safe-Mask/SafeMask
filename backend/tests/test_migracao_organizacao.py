"""Migração de banco legado para o modelo de organização.

Simula um banco criado antes da organização existir: as tabelas estão lá,
sem a coluna `organizacao_id` e sem a tabela `organizacao`. O que importa é
que nenhuma equipe ou usuário desapareça do menu de quem já os usava.

Os dados são inseridos com SQL cru de propósito: usar a ORM já escreveria a
coluna nova e o teste passaria sem exercitar a migração.
"""

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.database import (
    _ddl_adicionar_organizacao,
    _preencher_organizacoes_pendentes,
    garantir_indices,
    garantir_schema_organizacoes,
)
from app.models.organizacao import Organizacao

# Schema de antes da Fatia 5a: `organizacao` nao existe e `usuario`/`equipe`
# nao tem `organizacao_id`.
SCHEMA_LEGADO = [
    "CREATE TABLE cargo (cargo_id INTEGER PRIMARY KEY, nome VARCHAR(50) NOT NULL, "
    "nivel INTEGER NOT NULL, descricao TEXT)",
    "CREATE TABLE usuario (user_id INTEGER PRIMARY KEY, nome VARCHAR(120) NOT NULL, "
    "email VARCHAR(129) NOT NULL UNIQUE, senha_hash VARCHAR(255) NOT NULL, "
    "criado_em TIMESTAMP)",
    "CREATE TABLE equipe (team_id INTEGER PRIMARY KEY, nome VARCHAR(120) NOT NULL, "
    "descricao TEXT, criado_em TIMESTAMP)",
    "CREATE TABLE usuario_equipe (user_team_id INTEGER PRIMARY KEY, "
    "user_id INTEGER NOT NULL, team_id INTEGER NOT NULL, cargo_id INTEGER NOT NULL, "
    "criado_em TIMESTAMP)",
    "CREATE TABLE documentos (doc_id INTEGER PRIMARY KEY, user_team_id INTEGER NOT NULL, "
    "nome_original VARCHAR(255), extensao VARCHAR(16), tamanho_bytes INTEGER, "
    "nivel_seguranca INTEGER NOT NULL, chave_criptografica VARCHAR(255), "
    "hash_documento VARCHAR(128), caminho_storage VARCHAR(255), "
    "status_processamento VARCHAR(32), ativo BOOLEAN, criado_em TIMESTAMP, "
    "cpf_censurados INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE dado_sensivel (dado_id INTEGER PRIMARY KEY, doc_id INTEGER NOT NULL, "
    "tipo_entidade VARCHAR(32), conteudo_hash VARCHAR(128), pagina INTEGER, "
    "coordenadas TEXT, nivel_requerido INTEGER NOT NULL DEFAULT 4, criado_em TIMESTAMP)",
    "CREATE TABLE log_auditoria (log_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
    "acao VARCHAR(64) NOT NULL, ip_origem VARCHAR(64), criado_em TIMESTAMP)",
]


@pytest.fixture
def banco_legado(tmp_path, monkeypatch):
    """SQLite no schema antigo, com usuarios e equipes preexistentes."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'legado.db'}",
        connect_args={"check_same_thread": False},
    )

    with engine.begin() as conn:
        for ddl in SCHEMA_LEGADO:
            conn.exec_driver_sql(ddl)
        conn.exec_driver_sql("INSERT INTO cargo VALUES (1, 'lider', 3, 'lider')")
        for i in range(1, 4):
            conn.exec_driver_sql(
                "INSERT INTO usuario (user_id, nome, email, senha_hash) VALUES (?, ?, ?, ?)",
                (i, f"Usuario {i}", f"u{i}@x.com", "hash"),
            )
            conn.exec_driver_sql(
                "INSERT INTO equipe (team_id, nome) VALUES (?, ?)", (i, f"Equipe {i}")
            )
            conn.exec_driver_sql(
                "INSERT INTO usuario_equipe (user_team_id, user_id, team_id, cargo_id) "
                "VALUES (?, ?, ?, 1)",
                (i, i, i),
            )

    # As funcoes de migracao leem `app.database.engine` e `app.database.inspect`.
    monkeypatch.setattr("app.database.engine", engine)
    monkeypatch.setattr("app.database.inspect", lambda _engine: inspect(engine))
    return engine


def _sessao(engine):
    return sessionmaker(bind=engine)()


def test_criar_tabela_organizacao_e_colunas(banco_legado):
    garantir_schema_organizacoes()

    inspector = inspect(banco_legado)
    assert "organizacao" in inspector.get_table_names()
    assert "organizacao_id" in {c["name"] for c in inspector.get_columns("usuario")}
    assert "organizacao_id" in {c["name"] for c in inspector.get_columns("equipe")}


def test_migracao_preserva_todos_os_registros(banco_legado):
    antes = {}
    with banco_legado.begin() as conn:
        for tabela in ("usuario", "equipe", "usuario_equipe"):
            antes[tabela] = conn.execute(
                text(f"SELECT COUNT(*) FROM {tabela}")
            ).scalar_one()

    garantir_schema_organizacoes()

    with banco_legado.begin() as conn:
        for tabela, esperado in antes.items():
            assert conn.execute(
                text(f"SELECT COUNT(*) FROM {tabela}")
            ).scalar_one() == esperado


def test_migracao_vincula_tudo_a_organizacao_legada(banco_legado):
    garantir_schema_organizacoes()

    with banco_legado.begin() as conn:
        orgaos = conn.execute(
            text("SELECT organizacao_id FROM organizacao")
        ).scalars().all()
        # Um unico tenant de legado, e nada fica sem organizacao: um usuario
        # sem ela nao conseguiria mais abrir o menu de equipes.
        assert len(orgaos) == 1
        for tabela in ("usuario", "equipe"):
            assert conn.execute(
                text(f"SELECT COUNT(*) FROM {tabela} WHERE organizacao_id IS NULL")
            ).scalar_one() == 0


def test_backfill_e_idempotente(banco_legado):
    """Roda em todo boot: nao pode criar uma segunda organizacao legada."""
    from app.models.organizacao import Organizacao

    garantir_schema_organizacoes()

    _preencher_organizacoes_pendentes()
    _preencher_organizacoes_pendentes()

    db = _sessao(banco_legado)
    try:
        assert db.query(Organizacao).count() == 1
    finally:
        db.close()


def test_migracao_e_idempotente_no_schema(banco_legado):
    garantir_schema_organizacoes()
    garantir_schema_organizacoes()

    inspector = inspect(banco_legado)
    colunas = [c["name"] for c in inspector.get_columns("usuario")]
    assert colunas.count("organizacao_id") == 1


def test_indices_de_tenant_sao_criados(banco_legado):
    garantir_schema_organizacoes()
    garantir_indices()

    inspector = inspect(banco_legado)
    assert "idx_equipe_organizacao_id" in {i["name"] for i in inspector.get_indexes("equipe")}
    assert "idx_usuario_organizacao_id" in {i["name"] for i in inspector.get_indexes("usuario")}


def test_indices_de_tenant_sao_criados_apos_a_migracao(banco_legado):
    """A ordem no boot importa: `garantir_indices` antes falharia."""
    garantir_schema_organizacoes()

    inspector = inspect(banco_legado)
    colunas = {c["name"] for c in inspector.get_columns("equipe")}
    assert "organizacao_id" in colunas


# --- O DDL que vai para o Postgres ----------------------------------------


def test_ddl_postgres_e_idempotente():
    """Postgres aceita ADD COLUMN IF NOT EXISTS, entao rodar duas vezes e seguro."""
    ddl = _ddl_adicionar_organizacao("postgresql")

    assert ddl["usuario"] == (
        "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS organizacao_id INTEGER"
    )
    assert ddl["equipe"] == (
        "ALTER TABLE equipe ADD COLUMN IF NOT EXISTS organizacao_id INTEGER"
    )


def test_ddl_sqlite_remove_if_not_exists():
    """SQLite rejeita ADD COLUMN IF NOT EXISTS; o DDL precisa cair no filtro."""
    ddl = _ddl_adicionar_organizacao("sqlite")

    for sql in ddl.values():
        assert "IF NOT EXISTS" not in sql
        assert sql.startswith("ALTER TABLE ")


def test_ddl_nao_altera_tabelas_inexistentes():
    ddl = _ddl_adicionar_organizacao("postgresql")

    # A migracao itera sobre o schema, entao tocar em `documentos` aqui
    # denotaria que o tenant vazou para dados que ja tem escopo via equipe.
    assert set(ddl) == {"usuario", "equipe"}


def test_indice_de_tenant_esta_no_lista_de_garantir_indices():
    """Os indices de tenant precisam estar no que o boot executa."""
    import app.database as database

    fonte = database.__file__
    with open(fonte, encoding="utf-8") as handle:
        conteudo = handle.read()

    assert "idx_equipe_organizacao_id ON equipe(organizacao_id)" in conteudo
    assert "idx_usuario_organizacao_id ON usuario(organizacao_id)" in conteudo


def test_tabela_organizacao_compila_para_postgres():
    """Confere o CREATE TABLE da organizacao no dialeto de producao."""
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    ddl = str(
        CreateTable(Organizacao.__table__).compile(dialect=postgresql.dialect())
    )

    assert "CREATE TABLE organizacao" in ddl
    # SERIAL no Postgres: a coluna precisa ser NOT NULL e autoincremental.
    assert "organizacao_id SERIAL NOT NULL" in ddl
    assert "PRIMARY KEY (organizacao_id)" in ddl

