"""Regressoes de autenticacao descobertas em auditoria.

Achados que estes testes fixam:

1. Token de acesso e token de reset usavam a mesma assinatura e o mesmo
   claim `sub`. `reset_senha` decodificava qualquer JWT valido, entao o token
   de sessao da vitima — que vive no localStorage e vaza em qualquer XSS —
   virava senha permanente.
2. Resetar a senha nao invalidava nada: o mesmo token de reset funcionava N
   vezes e os access tokens ja emitidos continuavam valendo depois da troca.
   Quem roubou a senha antiga mantinha o acesso.
3. `/auth/login` sem limite de tentativas: password spraying direto.
4. `/auth/login` respondia mais rapido para e-mail inexistente (bcrypt so roda
   quando o usuario existe), enumerando cadastros por tempo.
5. `/auth/verificar-email` respondia {"existe": bool} sem autenticacao.
6. `senha_hash: str` sem `min_length` aceitava senha vazia no cadastro.
"""

import time

import pytest
from jose import jwt

from app.core.audit import ACAO_LOGIN_BLOQUEADO
from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    TIPO_ACCESS,
    TIPO_RESET,
    criar_token_jwt,
    criar_token_jwt_com_expiry,
)
from app.models.log_auditoria import LogAuditoria

# Senha do usuario semeado em `conftest.seed`.
SENHA = "SenhaForte123!"


@pytest.fixture
def login(client, seed):
    def _login(senha=SENHA, email=None):
        return client.post(
            "/auth/login",
            json={"email": email or seed["usuario"].email, "senha_hash": senha},
        )

    return _login


def _decodifica(token):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# --- 1. Token de acesso nao serve como token de reset -----------------------


def test_access_token_nao_reseta_senha(client, seed, login):
    """O token que ja autentica na API nao pode virar senha permanente."""
    acesso = login().json()["access_token"]
    assert _decodifica(acesso)["typ"] == TIPO_ACCESS

    resp = client.post(
        "/auth/reset-senha",
        json={"token": acesso, "senha": "SenhaDoAtacante123"},
    )
    assert resp.status_code == 400, resp.text

    # E a senha antiga continua valendo: nada foi trocado.
    assert login(senha=SENHA).status_code == 200
    assert login(senha="SenhaDoAtacante123").status_code == 401


def test_reset_token_nao_autentica(client, seed, login):
    """O inverso: token de recuperacao nao abre a API."""
    reset = criar_token_jwt_com_expiry({"sub": seed["usuario"].email}, minutes=30)
    assert _decodifica(reset)["typ"] == TIPO_RESET

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {reset}"}).status_code == 401


def test_me_exige_token_de_acesso(client, seed):
    assert client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {criar_token_jwt({'sub': seed['usuario'].email})}"},
    ).status_code == 200


# --- 2. Trocar a senha invalida o que ja estava em circulacao ----------------


def test_reset_invalida_o_token_de_sessao_anterior(client, seed, login):
    """O acesso roubado morre junto com a senha antiga."""
    acesso_antigo = login().json()["access_token"]
    reset = criar_token_jwt_com_expiry({"sub": seed["usuario"].email}, minutes=30)

    resp = client.post("/auth/reset-senha", json={"token": reset, "senha": "NovaSenha456"})
    assert resp.status_code == 200, resp.text

    headers = {"Authorization": f"Bearer {acesso_antigo}"}
    for rota in ("/auth/me", "/documentos/censurados", "/dashboard/overview"):
        assert client.get(rota, headers=headers).status_code == 401, rota


def test_login_novo_apos_reset_usa_a_senha_nova(client, seed, login):
    reset = criar_token_jwt_com_expiry({"sub": seed["usuario"].email}, minutes=30)
    client.post("/auth/reset-senha", json={"token": reset, "senha": "NovaSenha456"})

    assert login(senha=SENHA).status_code == 401
    novo = login(senha="NovaSenha456")
    assert novo.status_code == 200
    assert novo.json()["access_token"]
    assert client.get(
        "/auth/me", headers={"Authorization": f"Bearer {novo.json()['access_token']}"}
    ).status_code == 200


def test_reset_sobe_a_versao_do_token(client, seed, login):
    """A versao no token reflete a do usuario no banco."""
    antes = _decodifica(login().json()["access_token"])["tv"]

    reset = criar_token_jwt_com_expiry({"sub": seed["usuario"].email}, minutes=30)
    client.post("/auth/reset-senha", json={"token": reset, "senha": "NovaSenha456"})

    assert _decodifica(login(senha="NovaSenha456").json()["access_token"])["tv"] == antes + 1


# --- 3. Limite de tentativas -------------------------------------------------


def test_login_travou_apos_tentativas_repetidas(client, seed, login):
    for _ in range(6):
        assert login(senha="ErradaMesmo").status_code == 401

    resp = login(senha=SENHA)
    assert resp.status_code == 429, resp.text
    assert "Muitas tentativas" in resp.json()["detail"]


def test_tentativa_que_acerta_a_senha_tambem_passa(client, seed, login):
    """O bloqueio conta falhas, nao tentativas: acertar a senha entra."""
    for _ in range(4):
        login(senha="ErradaMesmo")

    assert login(senha=SENHA).status_code == 200


def test_login_bem_sucedido_zera_o_historico(client, seed, login):
    """Quem acerta a senha nao fica trancado por erros antigos.

    Sem isso, digitar errado duas vezes, acertar e errar de novo cinco vezes na
    mesma hora deixaria o usuario legitimate fora da propria conta.
    """
    for _ in range(4):
        login(senha="ErradaMesmo")
    assert login(senha=SENHA).status_code == 200

    for _ in range(4):
        login(senha="ErradaDepois")

    assert login(senha=SENHA).status_code == 200, resp_detalhe(client, seed)


def resp_detalhe(client, seed):
    r = client.post(
        "/auth/login", json={"email": seed["usuario"].email, "senha_hash": SENHA}
    )
    return r.text


def test_login_bloqueado_registra_auditoria(client, seed, login):
    for _ in range(6):
        login(senha="ErradaMesmo")
    login(senha=SENHA)

    acoes = [log.acao for log in seed["db"].query(LogAuditoria).all()]
    assert ACAO_LOGIN_BLOQUEADO in acoes


def test_tentativa_de_outro_email_nao_herda_o_bloqueio(client, seed):
    """Falhas de uma origem nao trancam a conta de outra origem.

    O limite e por (e-mail, IP): o spray vem de um host so, entao travar o IP
    corta o ataque. Testar isso exige IPs distintos, como em producao atras de
    proxies diferentes.
    """
    for _ in range(6):
        resp = client.post(
            "/auth/login",
            json={"email": "ninguem@x.com", "senha_hash": "ErradaMesmo"},
            headers={"X-Forwarded-For": "10.0.0.9"},
        )
        assert resp.status_code == 401

    ok = client.post(
        "/auth/login",
        json={"email": seed["usuario"].email, "senha_hash": SENHA},
        headers={"X-Forwarded-For": "10.0.0.10"},
    )
    assert ok.status_code == 200, ok.text


def test_login_valido_apos_poucas_tentativas(client, seed, login):
    login(senha="ErradaUma")
    login(senha="ErradaDuas")
    assert login(senha=SENHA).status_code == 200


# --- 4/5. Enumeracao de usuarios --------------------------------------------


def test_login_nao_enumera_por_tempo(client, seed):
    """O custo do bcrypt tem de ser o mesmo nos dois caminhos.

    Antes, `if not usuario or not verificar_senha(...)` encurtava o caminho do
    e-mail inexistente: o bcrypt nao rodava, e a resposta chegava ~400ms antes.
    Isso enumera cadastros sem precisar de endpoint nenhum.

    Medido: com o dummy verify a diferenca cai para ~60ms (sobra o trabalho de
    auditoria no banco). Sem ele, volta a ~390ms. O limite de 150ms separa os
    dois casos com folga.
    """
    def medir(email, repeticoes=5):
        amostras = []
        for _ in range(repeticoes):
            inicio = time.perf_counter()
            client.post("/auth/login", json={"email": email, "senha_hash": "Errada"})
            amostras.append(time.perf_counter() - inicio)
        return sorted(amostras)[repeticoes // 2]

    existente = medir(seed["usuario"].email)
    inexistente = medir("naoexiste@x.com")

    assert abs(existente - inexistente) < 0.15, (
        f"tempo revela quem tem cadastro: existente={existente:.3f}s "
        f"inexistente={inexistente:.3f}s"
    )


def test_login_nao_distingue_email_inexistente(client, seed, login):
    """Mesma resposta e mesmo status para e-mail desconhecido e senha errada."""
    inexistente = login(senha="Qualquer", email="ninguem@x.com")
    senha_errada = login(senha="Qualquer")

    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json()["detail"] == senha_errada.json()["detail"]


def test_verificar_email_nao_existe_mais(client):
    """O oraculo de enumeracao saiu: sobraria so `POST /auth/cadastro`."""
    assert client.get("/auth/verificar-email/ana@safemask.example.com").status_code == 404


def test_recuperar_senha_continua_neutro(client, seed):
    ok = client.post("/auth/recuperar-senha", json={"email": seed["usuario"].email})
    desconhecido = client.post("/auth/recuperar-senha", json={"email": "ninguem@x.com"})
    assert ok.json()["mensagem"] == desconhecido.json()["mensagem"]


# --- 6. Senha vazia ou curta -------------------------------------------------


@pytest.mark.parametrize("senha", ["", "abc", "1234567"])
def test_cadastro_rejeita_senha_curta(client, seed, senha):
    resp = client.post(
        "/auth/cadastro",
        json={"nome": "Novo", "email": "novo@x.com", "senha_hash": senha},
    )
    assert resp.status_code == 422, resp.text


def test_cadastro_nao_persiste_senha_vazia(client, seed):
    """Nada e criado, e o login com senha vazia nem chega a consultar."""
    assert client.post(
        "/auth/cadastro", json={"nome": "Novo", "email": "novo@x.com", "senha_hash": ""}
    ).status_code == 422
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {criar_token_jwt({'sub': 'novo@x.com'})}"}).status_code == 401
    assert client.post(
        "/auth/login", json={"email": "novo@x.com", "senha_hash": ""}
    ).status_code == 422


@pytest.mark.parametrize("payload", [
    {"senha": "SenhaNova123"},
    {"token": "x"},
    {"token": "", "senha": "SenhaNova123"},
])
def test_reset_senha_exige_o_payload_completo(client, payload):
    assert client.post("/auth/reset-senha", json=payload).status_code == 422


def test_reset_senha_rejeita_senha_curta(client, seed):
    reset = criar_token_jwt_com_expiry({"sub": seed["usuario"].email}, minutes=30)
    resp = client.post("/auth/reset-senha", json={"token": reset, "senha": "123"})
    assert resp.status_code == 422, resp.text
