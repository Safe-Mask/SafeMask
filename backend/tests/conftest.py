"""Infraestrutura de testes do backend.

Os testes rodam sobre SQLite em arquivo temporario para nao depender de um
Postgres local. `dado_sensivel.coordenadas` usa `postgresql.JSONB`, que nao
compila em SQLite, entao registramos um compilador que emite `JSON`.

Este arquivo precisa definir DATABASE_URL antes de qualquer import de
`app.*`, porque `app.database` le a variavel no momento do import.
"""

import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / "safemask_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ.setdefault("SECRET_KEY", "segredo-de-teste-nao-usar-em-producao")
os.environ.setdefault("BREVO_API_KEY", "teste")
os.environ.setdefault("SMTP_FROM", "teste@safemask.local")
os.environ.setdefault("SMTP_FROM_NAME", "SafeMask Teste")

from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kwargs):  # noqa: ANN001, ANN003, ANN202
    return "JSON"


import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.cargo import Cargo  # noqa: E402
from app.models.dado_sensivel import DadoSensivel  # noqa: E402
from app.models.documentos import Documento  # noqa: E402
from app.models.equipe import Equipe  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.usuario_equipe import UsuarioEquipe  # noqa: E402


@pytest.fixture
def db_session(tmp_path):
    """Sessao limpa em SQLite, com todas as tabelas criadas."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session, monkeypatch, tmp_path):
    """TestClient com o banco de teste e diretorios de upload temporarios."""
    from app.routes import documentos as documentos_routes

    # Isola os arquivos em disco: nada deve vazar para backend/uploads/.
    monkeypatch.setattr(documentos_routes, "ORIGINAIS_DIR", tmp_path / "originais")
    monkeypatch.setattr(documentos_routes, "CENSURADOS_DIR", tmp_path / "censurados")
    (tmp_path / "originais").mkdir(parents=True, exist_ok=True)
    (tmp_path / "censurados").mkdir(parents=True, exist_ok=True)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed(db_session):
    """Cargos, equipes e um usuario com vinculo em duas equipes.

    Retorna um dict com os ids criados para uso nos testes.
    """

    def _criar(nome: str, nivel: int) -> Cargo:
        cargo = Cargo(nome=nome, nivel=nivel, descricao=nome)
        db_session.add(cargo)
        return cargo

    lider = _criar("lider", 3)
    supervisor = _criar("supervisor", 2)
    membro = _criar("membro", 1)

    equipe_a = Equipe(nome="Equipe A", descricao="A")
    equipe_b = Equipe(nome="Equipe B", descricao="B")
    db_session.add_all([equipe_a, equipe_b])

    usuario = Usuario(nome="Ana", email="ana@safemask.local", senha_hash="hash-de-teste")
    db_session.add(usuario)
    db_session.flush()

    vinculo_a = UsuarioEquipe(user_id=usuario.user_id, team_id=equipe_a.team_id, cargo_id=lider.cargo_id)
    vinculo_b = UsuarioEquipe(user_id=usuario.user_id, team_id=equipe_b.team_id, cargo_id=membro.cargo_id)
    db_session.add_all([vinculo_a, vinculo_b])
    db_session.commit()

    return {
        "db": db_session,
        "usuario": usuario,
        "equipe_a": equipe_a,
        "equipe_b": equipe_b,
        "user_team_a": vinculo_a.user_team_id,
        "user_team_b": vinculo_b.user_team_id,
        "cargo_lider": lider,
        "cargo_supervisor": supervisor,
        "cargo_membro": membro,
    }


@pytest.fixture
def dados_sensiveis():
    """Fabrica linhas de DadoSensivel ja vinculadas a um Documento."""

    def _criar(doc_id: int, nivel_requerido: int, pagina: int = 1, coordenadas=None):
        return DadoSensivel(
            doc_id=doc_id,
            tipo_entidade="CPF",
            conteudo_hash="hash-de-teste",
            pagina=pagina,
            coordenadas=coordenadas or [10, 10, 100, 20],
            nivel_requerido=nivel_requerido,
        )

    return _criar


@pytest.fixture
def documento():
    """Fabrica um registro de Documento."""

    def _criar(user_team_id: int, **kwargs):
        defaults = {
            "nome_original": "contrato.pdf",
            "extensao": "pdf",
            "tamanho_bytes": 10,
            "nivel_seguranca": 1,
            "chave_criptografica": "chave",
            "hash_documento": "hash-doc",
            "caminho_storage": "",
            "status_processamento": "CONCLUIDO",
            "cpf_censurados": 0,
        }
        defaults.update(kwargs)
        return Documento(user_team_id=user_team_id, **defaults)

    return _criar
