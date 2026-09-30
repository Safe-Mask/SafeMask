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
from app.models.organizacao import Organizacao  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.usuario_equipe import UsuarioEquipe  # noqa: E402

CONTEUDO_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"

# Senha dos usuarios semeados. Antes era um hash bcrypt literal cujo texto
# original ninguem conhecia: o usuario existia mas nao dava para logar, e
# nenhum teste de login cobria o caminho real de senha.
SENHA_SEED = "SenhaForte123!"
CONTEUDO_CENSURADO = b"%PDF-1.4\nconteudo-tarjado-pelo-scanner\n%%EOF\n"

# E-mails enviados durante a suite, para o teste inspecionar.
EMAILS_ENVIADOS: list[dict] = []


@pytest.fixture(autouse=True)
def sem_envio_de_email_real(monkeypatch):
    """Impede a suite de chamar o SendGrid de verdade.

    Sem isto, qualquer teste que dispare `/auth/recuperar-senha` para um e-mail
    que existe faz uma chamada HTTPS para a internet: a suite fica lenta,
    dependente de rede e sujeita ao limite de taxa da conta. E o 401 da API
    vazava na saida do teste como se fosse falha nossa.
    """
    from app.routes import auth as auth_routes

    def _fake(destinatario, nome, token):
        EMAILS_ENVIADOS.append(
            {"destinatario": destinatario, "nome": nome, "token": token}
        )

    monkeypatch.setattr(auth_routes, "enviar_email_recuperacao", _fake)
    monkeypatch.setattr("app.core.email.enviar_email_recuperacao", _fake, raising=False)
    yield


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


def _senha_seed() -> str:
    """Hash da senha semeada, calculado uma vez por sessao de teste."""
    global _SENHA_HASH_CACHE
    if _SENHA_HASH_CACHE is None:
        from app.core.security import hash_senha

        _SENHA_HASH_CACHE = hash_senha(SENHA_SEED)
    return _SENHA_HASH_CACHE


_SENHA_HASH_CACHE = None


@pytest.fixture
def seed(db_session):
    """Cargos, duas organizacoes, equipes e usuarios de cada uma.

    A segunda organizacao existe para que os testes de isolamento tenham o que
    comparar: sem um segundo tenant, um filtro de organizacao ausente passaria
    despercebido.
    """

    def _criar(nome: str, nivel: int) -> Cargo:
        cargo = Cargo(nome=nome, nivel=nivel, descricao=nome)
        db_session.add(cargo)
        return cargo

    lider = _criar("lider", 3)
    supervisor = _criar("supervisor", 2)
    membro = _criar("membro", 1)

    org_acme = Organizacao(nome="Acme")
    org_globex = Organizacao(nome="Globex")
    db_session.add_all([org_acme, org_globex])
    db_session.flush()

    equipe_a = Equipe(nome="Equipe A", descricao="A", organizacao_id=org_acme.organizacao_id)
    equipe_b = Equipe(nome="Equipe B", descricao="B", organizacao_id=org_acme.organizacao_id)
    equipe_globex = Equipe(nome="Equipe Globex", descricao="G", organizacao_id=org_globex.organizacao_id)
    db_session.add_all([equipe_a, equipe_b, equipe_globex])

    usuario = Usuario(
        nome="Ana",
        email="ana@safemask.example.com",
        senha_hash=_senha_seed(),
        organizacao_id=org_acme.organizacao_id,
    )
    usuario_globex = Usuario(
        nome="Bia",
        email="bia@safemask.example.com",
        senha_hash=_senha_seed(),
        organizacao_id=org_globex.organizacao_id,
    )
    db_session.add_all([usuario, usuario_globex])
    db_session.flush()

    vinculo_a = UsuarioEquipe(user_id=usuario.user_id, team_id=equipe_a.team_id, cargo_id=lider.cargo_id)
    vinculo_b = UsuarioEquipe(user_id=usuario.user_id, team_id=equipe_b.team_id, cargo_id=membro.cargo_id)
    vinculo_globex = UsuarioEquipe(
        user_id=usuario_globex.user_id,
        team_id=equipe_globex.team_id,
        cargo_id=lider.cargo_id,
    )
    db_session.add_all([vinculo_a, vinculo_b, vinculo_globex])
    db_session.commit()

    return {
        "db": db_session,
        "usuario": usuario,
        "usuario_globex": usuario_globex,
        "organizacao": org_acme,
        "organizacao_globex": org_globex,
        "equipe_a": equipe_a,
        "equipe_b": equipe_b,
        "equipe_globex": equipe_globex,
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


class ScannerFalso:
    """Substitui o DocumentScanner para nao depender de torch/pdfplumber.

    Reproduz o contrato real: cria um `Documento`, cria `DadoSensivel` linked
    a esse unico doc_id e grava o PDF tarjado em `dir_censurado`.
    """

    def __init__(self, itens_sensiveis, doc_id_atribuido=None):
        self.itens_sensiveis = itens_sensiveis
        self.doc_id_atribuido = doc_id_atribuido
        self.chamadas = 0
        self.itens_para_cobrir = None

    def scan_and_save(self, file_path, db, user_team_id, nome_original,
                      nivel_seguranca, dir_original, dir_censurado):
        from pathlib import Path

        self.chamadas += 1
        import hashlib

        conteudo = Path(file_path).read_bytes()
        hash_documento = hashlib.sha256(conteudo).hexdigest()

        doc = Documento(
            user_team_id=user_team_id,
            nome_original=nome_original,
            extensao="pdf",
            tamanho_bytes=len(conteudo),
            nivel_seguranca=nivel_seguranca,
            chave_criptografica="chave",
            hash_documento=hash_documento,
            caminho_storage=str(Path(dir_censurado) / f"{hash_documento}_tarjado.pdf"),
            status_processamento="CONCLUIDO",
            cpf_censurados=len(self.itens_sensiveis),
        )
        db.add(doc)
        db.flush()

        for nivel_requerido, pagina in self.itens_sensiveis:
            db.add(
                DadoSensivel(
                    doc_id=doc.doc_id,
                    tipo_entidade="CPF",
                    conteudo_hash="hash",
                    pagina=pagina,
                    coordenadas=[10, 10, 100, 20],
                    espaco_coordenadas="pdf",
                    nivel_requerido=nivel_requerido,
                )
            )
        db.flush()

        Path(dir_censurado).mkdir(parents=True, exist_ok=True)
        Path(doc.caminho_storage).write_bytes(CONTEUDO_CENSURADO)

        return {
            "doc_id": doc.doc_id,
            "hash": hash_documento,
            "total_sensiveis": len(self.itens_sensiveis),
            "cpf_censurados": len(self.itens_sensiveis),
            "status": "CONCLUIDO",
        }

    def gerar_pdf_parcial(self, file_path, itens_para_cobrir, dir_destino, nome_saida):
        from pathlib import Path

        # Guarda o que a rota mandou, para o teste ver o espaco de cada caixa.
        self.itens_para_cobrir = itens_para_cobrir

        Path(dir_destino).mkdir(parents=True, exist_ok=True)
        destino = Path(dir_destino) / nome_saida
        destino.write_bytes(b"%PDF-1.4\nparcial\n%%EOF\n")
        return destino


@pytest.fixture
def scanner_registrado(monkeypatch):
    """Instala um ScannerFalso e devolve a fabrica."""

    def _instalar(itens_sensiveis):
        from app.routes import documentos as documentos_routes

        scanner = ScannerFalso(itens_sensiveis)
        monkeypatch.setattr(documentos_routes, "get_scanner", lambda: scanner)
        return scanner

    return _instalar
