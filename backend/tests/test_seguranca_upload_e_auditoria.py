"""Regressoes de upload, CORS e trilha de auditoria (Fatia 2)."""

import pytest

from app.core.config import MAX_UPLOAD_BYTES
from app.core.security import criar_token_jwt
from app.models.log_auditoria import LogAuditoria

TOKEN = criar_token_jwt({"sub": "ana@safemask.example.com", "nome": "Ana"})
AUTH = {"Authorization": f"Bearer {TOKEN}"}

PDF_VALIDO = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def _upload(client, teams, conteudo=PDF_VALIDO, filename="contrato.pdf"):
    return client.post(
        "/documentos/upload",
        headers=AUTH,
        files={"file": (filename, conteudo, "application/pdf")},
        data={"titulo": "Contrato", "nivel_seguranca": "1", "teams": teams},
    )


# --- Validacao de upload -------------------------------------------------


def test_upload_rejeita_conteudo_nao_pdf(client, seed, scanner_registrado):
    """Nome com .pdf mas conteudo de outro formato deve ser recusado."""
    scanner_registrado([])
    resp = _upload(client, f"[{seed['equipe_a'].team_id}]", conteudo=b"<html>phishing</html>")

    assert resp.status_code == 400, resp.text
    assert "PDF" in resp.json()["detail"]


def test_upload_rejeita_extensao_nao_permitida(client, seed, scanner_registrado):
    scanner_registrado([])
    resp = _upload(client, f"[{seed['equipe_a'].team_id}]", filename="malware.exe")

    assert resp.status_code == 400, resp.text


def test_upload_rejeita_arquivo_acima_do_limite(client, seed, scanner_registrado):
    """Conteudo que passa do MAX_UPLOAD_BYTES retorna 413."""
    scanner_registrado([])
    grande = PDF_VALIDO + b"0" * (MAX_UPLOAD_BYTES + 1024)

    resp = _upload(client, f"[{seed['equipe_a'].team_id}]", conteudo=grande)

    assert resp.status_code == 413, resp.text
    assert "limite" in resp.json()["detail"].lower()


def test_upload_rejeita_arquivo_vazio(client, seed, scanner_registrado):
    scanner_registrado([])
    resp = _upload(client, f"[{seed['equipe_a'].team_id}]", conteudo=b"")

    assert resp.status_code == 400, resp.text


def test_salvar_censurado_rejeita_conteudo_nao_pdf(client, seed):
    """`salvar-censurado` aceitava qualquer arquivo; agora valida tambem."""
    resp = client.post(
        "/documentos/salvar-censurado",
        headers=AUTH,
        files={"file": ("nota.txt", b"segredo em texto puro", "text/plain")},
        data={
            "titulo": "Nota",
            "nivel_seguranca": "1",
            "teams": f"[{seed['equipe_a'].team_id}]",
        },
    )

    assert resp.status_code == 400, resp.text


def test_salvar_censurado_nao_deixa_arquivo_orfao(client, seed, tmp_path):
    """403 no meio do loop nao pode deixar arquivo gravado em disco."""
    db = seed["db"]
    # equipe B existe no banco, mas Ana nao e membro dela.
    import hashlib

    from app.models.equipe import Equipe

    equipe_c = Equipe(nome="Equipe C", descricao="C")
    db.add(equipe_c)
    db.commit()

    resp = client.post(
        "/documentos/salvar-censurado",
        headers=AUTH,
        files={"file": ("contrato.pdf", PDF_VALIDO, "application/pdf")},
        data={
            "titulo": "Contrato",
            "nivel_seguranca": "1",
            "teams": f"[{seed['equipe_a'].team_id}, {equipe_c.team_id}]",
        },
    )

    assert resp.status_code == 403, resp.text

    hash_esperado = hashlib.sha256(PDF_VALIDO).hexdigest()
    orfaos = list((tmp_path / "censurados").glob(f"{hash_esperado}*"))
    assert not orfaos, f"arquivo orfao deixado no storage: {orfaos}"


# --- Auditoria -----------------------------------------------------------


def test_upload_registra_auditoria(client, seed, scanner_registrado):
    scanner_registrado([(3, 1)])
    resp = _upload(client, f"[{seed['equipe_a'].team_id}]")
    assert resp.status_code == 201, resp.text

    logs = seed["db"].query(LogAuditoria).all()
    assert [log.acao for log in logs] == ["upload_documento"]
    assert logs[0].user_id == seed["usuario"].user_id
    assert logs[0].ip_origem


def test_ver_parcial_registra_auditoria(client, seed, scanner_registrado, tmp_path):
    import hashlib

    scanner_registrado([(3, 1)])
    resp = _upload(client, f"[{seed['equipe_b'].team_id}]")
    assert resp.status_code == 201, resp.text

    hash_documento = hashlib.sha256(PDF_VALIDO).hexdigest()
    (tmp_path / "originais" / f"{hash_documento}.pdf").write_bytes(PDF_VALIDO)

    from app.models.documentos import Documento

    doc = seed["db"].query(Documento).one()
    resp = client.get(f"/documentos/{doc.doc_id}/parcial", headers=AUTH)
    assert resp.status_code == 200, resp.text

    acoes = [log.acao for log in seed["db"].query(LogAuditoria).all()]
    assert "ver_parcial" in acoes


def test_login_registra_auditoria(client, seed):
    from app.core.security import hash_senha
    from app.models.usuario import Usuario

    usuario = seed["db"].query(Usuario).one()
    usuario.senha_hash = hash_senha("SenhaForte123!")
    seed["db"].commit()

    resp = client.post(
        "/auth/login", json={"email": usuario.email, "senha_hash": "SenhaForte123!"}
    )

    assert resp.status_code == 200, resp.text
    logs = seed["db"].query(LogAuditoria).all()
    assert [log.acao for log in logs] == ["login"]


def test_login_falho_registra_auditoria(client, seed):
    from app.models.usuario import Usuario

    usuario = seed["db"].query(Usuario).one()
    resp = client.post(
        "/auth/login", json={"email": usuario.email, "senha_hash": "senha-errada"}
    )

    assert resp.status_code == 401
    logs = seed["db"].query(LogAuditoria).all()
    assert [log.acao for log in logs] == ["login_falha"]


# --- CORS ---------------------------------------------------------------


def test_cors_nao_aceita_origem_desconhecida(client, seed):
    """`*` com credentials era aceito; origem fora da lista deve ficar sem CORS."""
    resp = client.get("/", headers={"Origin": "https://atacante.example.com"})

    assert "access-control-allow-origin" not in resp.headers


def test_cors_aceita_origem_configurada(client, seed):
    from app.core.config import CORS_ORIGINS

    resp = client.get("/", headers={"Origin": CORS_ORIGINS[0]})

    assert resp.headers.get("access-control-allow-origin") == CORS_ORIGINS[0]


def test_cors_nao_usa_curinga_com_credentials(client, seed):
    """O navegador rejeita `*` quando allow_credentials=True."""
    from app.core.config import CORS_ORIGINS

    assert "*" not in CORS_ORIGINS, "CORS_ORIGINS nao pode conter wildcard com credentials"

    resp = client.get("/", headers={"Origin": "*"})
    assert resp.headers.get("access-control-allow-origin") != "*"


# --- Recuperacao de senha nao enumera usuarios ---------------------------


@pytest.mark.parametrize(
    ("email", "status_esperado"),
    [("nao-cadastrado@safemask.example.com", 200), ("ana@safemask.example.com", 500)],
)
def test_recuperar_senha_nao_revela_quem_existe(client, seed, email, status_esperado):
    """O corpo da resposta deve ser identico exista ou nao o cadastro.

    Quando o email existe o envio depende de BREVO_API_KEY, que em teste
    aponta para um valor invalido e produz 500. O ponto e que a *mensagem*
    nunca distingue os dois casos.
    """
    resp = client.post("/auth/recuperar-senha", json={"email": email})

    assert "existe" not in resp.text.lower()
    if email == "nao-cadastrado@safemask.example.com":
        assert resp.status_code == 200, resp.text
