import json
import logging
import os
import urllib.error
import urllib.request
from email.message import EmailMessage

logger = logging.getLogger(__name__)

RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip() or None
RESEND_FROM = "SafeMask <anzen.na.masuku@gmail.com>"
RESEND_API_URL = "https://api.resend.com/emails"

logger.info("Email config: resend=%s from=%s", "set" if RESEND_API_KEY else "unset", RESEND_FROM)


def enviar_email_recuperacao(destinatario: str, nome: str) -> None:
    if not RESEND_API_KEY:
        raise ValueError("Configuração do Resend incompleta.")

    mensagem = EmailMessage()
    mensagem["Subject"] = "SafeMask - Recuperação de senha"
    mensagem["From"] = RESEND_FROM
    mensagem["To"] = destinatario

    linhas = [
        f"Olá, {nome}.",
        "",
        "Recebemos uma solicitação de recuperação de senha para a sua conta SafeMask.",
        "Se foi você, responda este email ou entre em contato com o suporte para seguir com a recuperação.",
    ]

    mensagem.set_content("\n".join(linhas))

    payload = {
        "from": RESEND_FROM,
        "to": [destinatario],
        "subject": mensagem["Subject"],
        "text": mensagem.get_content(),
    }

    request = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status_code = getattr(response, "status", response.getcode())
            if status_code >= 400:
                raise RuntimeError(f"Resend retornou status HTTP {status_code}.")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        logger.exception(
            "Falha ao enviar email de recuperação via Resend (status=%s). Resposta: %s",
            exc.code,
            body,
        )
        raise
    except Exception:
        logger.exception(
            "Falha ao enviar email de recuperação via Resend. Verifique conectividade de rede e a API key.",
        )
        raise