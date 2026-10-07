"""Smoke test E2E da API SafeMask contra um backend em execucao.

Uso:
  python scripts/e2e.py --base-url http://localhost:8000
  python scripts/e2e.py --base-url https://safemask-backend.onrender.com

Coverde o fluxo do pitch: cadastro -> login -> me -> equipes -> upload de PDF
com texto (regex) -> upload de PDF so-imagem (OCR) -> listar -> preview ->
parcial -> upload compartilhado entre equipes.

O teste de deploy exige a versao da nuvem (regex-only); a local adiciona a
deteccao por rede neural implicitamente. Ambas devem passar neste script.
"""

import argparse
import sys
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
DEMO_DIR = Path("/tmp/safemask-demo")


def _fazer_cadastro(client: httpx.Client, base: str, rotulo: str) -> dict:
    email = f"pitch.{rotulo}.{int(time.time())}@safemask.example.com"
    senha = "SenhaForte123!"
    resp = client.post(
        f"{base}/auth/cadastro",
        json={"nome": f"Usuario {rotulo}", "email": email, "senha_hash": senha},
        timeout=60,
    )
    resp.raise_for_status()
    corpo = resp.json()
    assert "access_token" in corpo, corpo
    return {"token": corpo["access_token"], "email": email, "senha": senha, **corpo["user"]}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _equipe_do_usuario(client: httpx.Client, base: str, token: str) -> int:
    resp = client.get(f"{base}/equipes/overview", headers=_auth(token), timeout=30)
    resp.raise_for_status()
    equipes = (resp.json() or {}).get("equipes", [])
    if not equipes:
        raise RuntimeError(f"usuario sem equipe: {resp.json()}")
    return equipes[0]["team_id"]


def _upload(client: httpx.Client, base: str, token: str,
            caminho: Path, titulo: str, equipes_texto: str) -> dict:
    conteudo = caminho.read_bytes()
    with caminho.open("rb") as fh:
        resp = client.post(
            f"{base}/documentos/upload",
            headers=_auth(token),
            files={"file": (caminho.name, fh, "application/pdf")},
            data={"titulo": titulo, "nivel_seguranca": "1", "teams": equipes_texto},
            timeout=300,
        )
    if resp.status_code != 201:
        raise RuntimeError(f"upload {caminho.name} -> {resp.status_code}: {resp.text}")
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    if not DEMO_DIR.exists():
        print(f"PDFs de exemplo nao encontrados em {DEMO_DIR}; gere com scripts/gerar_pdf_exemplo.py")
        return 2
    relatorio = DEMO_DIR / "relatorio_medico.pdf"
    receita = DEMO_DIR / "receita_escaneada.pdf"
    for p in (relatorio, receita):
        if not p.exists():
            print(f"Faltou {p}")
            return 2

    passo = 0
    with httpx.Client() as client:
        def ok(nome: str):
            nonlocal passo
            passo += 1
            print(f"  ok {passo}. {nome}")

        print("Checando health...")
        resp = client.get(f"{base}/", timeout=60)
        resp.raise_for_status()
        ok("GET / (health)")

        resp = client.get(f"{base}/docs", timeout=60)
        resp.raise_for_status()
        ok("GET /docs (Swagger)")

        usuario = _fazer_cadastro(client, base, "e2e")
        token = usuario["token"]
        ok(f"POST /auth/cadastro ({usuario['email']})")

        resp = client.post(
            f"{base}/auth/login",
            json={"email": usuario["email"], "senha_hash": usuario["senha"]},
            timeout=30,
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        ok("POST /auth/login")

        resp = client.get(f"{base}/auth/me", headers=_auth(token), timeout=30)
        resp.raise_for_status()
        ok("GET /auth/me")

        resp = client.get(f"{base}/dashboard/overview", headers=_auth(token), timeout=30)
        resp.raise_for_status()
        ok("GET /dashboard/overview")

        team_id = _equipe_do_usuario(client, base, token)
        ok(f"GET /equipes/overview (team_id={team_id})")

        doc = _upload(client, base, token, relatorio, "Relatorio Medico", f"[{team_id}]")
        assert doc["total_sensiveis"] > 0, (
            f"total_sensiveis deveria ser > 0 (contador), veio {doc['total_sensiveis']}: {doc}"
        )
        assert doc["status"] == "CONCLUIDO", doc
        ok(f"upload PDF com texto -> {doc['total_sensiveis']} dados sensiveis")

        doc_ocr = _upload(client, base, token, receita, "Receita Escaneada", f"[{team_id}]")
        assert doc_ocr["status"] == "CONCLUIDO", doc_ocr
        ok(f"upload PDF so-imagem (OCR) -> status {doc_ocr['status']}")

        resp = client.get(f"{base}/documentos/censurados", headers=_auth(token), timeout=30)
        resp.raise_for_status()
        lista = resp.json()
        ids = [d["doc_id"] for d in lista.get("documentos", [])]
        assert doc["doc_id"] in ids, f"doc recém-upload nao aparece na listagem: {lista}"
        ok("GET /documentos/censurados (lista)")

        r = client.get(
            f"{base}/documentos/censurados/{doc['doc_id']}/arquivo",
            headers=_auth(token), timeout=60,
        )
        if r.status_code != 200 or not r.content.startswith(b"%PDF"):
            raise RuntimeError(f"preview do arquivo censurado -> {r.status_code}")
        ok("preview do documento censurado (PDF valido)")

        resp = client.get(
            f"{base}/documentos/censurados/{doc['doc_id']}", headers=_auth(token), timeout=30
        )
        resp.raise_for_status()
        ok("GET /documentos/censurados/{id} (detalhe)")

        resp = client.get(
            f"{base}/documentos/{doc['doc_id']}/parcial", headers=_auth(token), timeout=60
        )
        assert resp.status_code == 200, resp.text
        assert resp.content.startswith(b"%PDF"), "parcial nao devolveu um PDF"
        ok("GET /documentos/{id}/parcial (descensura por cargo)")

        resp = client.get(
            f"{base}/documentos/{doc['doc_id']}/original", headers=_auth(token), timeout=60
        )
        assert resp.status_code == 200, resp.text
        ok("GET /documentos/{id}/original (lider enxerga o original)")

        resp = client.post(
            f"{base}/equipes",
            headers=_auth(token),
            json={"nome": "Equipe de teste E2E", "descricao": "criada pelo smoke test"},
            timeout=30,
        )
        resp.raise_for_status()
        equipe_nova = resp.json()
        team2_id = equipe_nova["equipe"]["team_id"]
        ok(f"POST /equipes (team_id={team2_id})")

        doc_comp = _upload(
            client, base, token, relatorio, "Relatorio Compartilhado",
            f"[{team_id},{team2_id}]",
        )
        ok(f"upload compartilhado entre 2 equipes -> {doc_comp['total_sensiveis']} sensiveis")

    print()
    print(f"E2E OK em {base}: {passo} etapas passaram.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (httpx.HTTPError, AssertionError, RuntimeError) as exc:
        print(f"\nE2E FALHOU: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc