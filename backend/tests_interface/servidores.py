"""Servidores do teste de interface (PI-III #16): API e telas, num ambiente descartavel.

- banco SQLite e pasta de arquivos temporarios; contas ficticias criadas antes
  de a API subir, numa organizacao propria;
- a API roda com SQLite (o tipo JSONB vira JSON, como no conftest dos testes);
- as telas sao servidas a partir do repositorio, com o `config.js` apontando
  para a porta da API do teste (o arquivo do repositorio nao e alterado).

Nada aqui toca o banco de desenvolvimento nem `backend/uploads`.
"""

import functools
import http.server
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
SENHA = "SenhaDeTeste123!"
CONTAS = {
    "lider": ("Lia Lider", "lider.ui@safemask.example.com"),
    "membro": ("Mara Membro", "membro.ui@safemask.example.com"),
}
EQUIPE = "Equipe Interface"

# Antes de importar a app: o JSONB do Postgres vira JSON no SQLite.
PREAMBULO = f"""
import sys
sys.path.insert(0, r"{BACKEND}")
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def _jsonb_sqlite(type_, compiler, **kwargs):
    return "JSON"
"""

SEMEAR = PREAMBULO + f"""
import app.main  # cria as tabelas e os cargos
from app.core.security import hash_senha
from app.database import SessionLocal
from app.models.cargo import Cargo
from app.models.equipe import Equipe
from app.models.organizacao import Organizacao
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe

db = SessionLocal()
cargos = {{c.nome: c for c in db.query(Cargo).all()}}
org = Organizacao(nome="Organizacao Interface")
db.add(org); db.flush()
equipe = Equipe(nome="{EQUIPE}", organizacao_id=org.organizacao_id)
db.add(equipe); db.flush()
for cargo, (nome, email) in {CONTAS!r}.items():
    u = Usuario(nome=nome, email=email, senha_hash=hash_senha("{SENHA}"), organizacao_id=org.organizacao_id)
    db.add(u); db.flush()
    db.add(UsuarioEquipe(user_id=u.user_id, team_id=equipe.team_id, cargo_id=cargos[cargo].cargo_id))
db.commit()
print(equipe.team_id)
"""

RODAR_API = PREAMBULO + """
import uvicorn
uvicorn.run("app.main:app", host="127.0.0.1", port=int(sys.argv[1]), log_level="warning")
"""


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _esperar(url: str, segundos: int = 120) -> None:
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"servidor nao respondeu: {url}")


class _Telas(http.server.SimpleHTTPRequestHandler):
    api_url = ""

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.split("?")[0] == "/frontend/js/config.js":
            dados = f"const API_ROOT = '{self.api_url}';\n".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
            return
        super().do_GET()


class Ambiente:
    """Sobe a API (subprocesso) e as telas (thread); `encerrar()` derruba tudo."""

    def __init__(self, pasta: Path):
        self.pasta = pasta
        self.porta_api = porta_livre()
        self.porta_telas = porta_livre()
        self.api_url = f"http://127.0.0.1:{self.porta_api}"
        self.telas_url = f"http://127.0.0.1:{self.porta_telas}"
        self.env = dict(
            os.environ,
            DATABASE_URL=f"sqlite:///{(pasta / 'ui.db').as_posix()}",
            SAFEMASK_PASTA_UPLOADS=str(pasta / "uploads"),
            SECRET_KEY="chave-do-teste-de-interface-000000000000000",
            ENVIRONMENT="development",
        )
        self._api = None
        self._telas = None

    def iniciar(self) -> "Ambiente":
        saida = subprocess.run([sys.executable, "-c", SEMEAR], env=self.env, cwd=self.pasta,
                               capture_output=True, text=True, timeout=180)
        if saida.returncode != 0:
            raise RuntimeError(saida.stderr[-2000:])
        self.team_id = int(saida.stdout.strip().splitlines()[-1])

        self._api = subprocess.Popen(
            [sys.executable, "-c", RODAR_API, str(self.porta_api)], env=self.env, cwd=BACKEND,
        )
        handler = type("Telas", (_Telas,), {"api_url": self.api_url})
        self._telas = http.server.ThreadingHTTPServer(
            ("127.0.0.1", self.porta_telas), functools.partial(handler, directory=str(RAIZ)),
        )
        threading.Thread(target=self._telas.serve_forever, daemon=True).start()
        _esperar(f"{self.api_url}/")
        _esperar(f"{self.telas_url}/index.html")
        return self

    def encerrar(self) -> None:
        if self._telas:
            self._telas.shutdown()
        if self._api:
            self._api.terminate()
            try:
                self._api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._api.kill()
