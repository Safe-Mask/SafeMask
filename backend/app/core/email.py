import os
import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict:
    """Read SMTP config fresh from environment on every call."""
    smtp_user = (os.getenv("SMTP_USER") or "").strip() or None
    smtp_from = (os.getenv("SMTP_FROM") or smtp_user or "").strip()
    return {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": smtp_user,
        "password": (os.getenv("SMTP_PASSWORD") or "").replace(" ", "").strip() or None,
        "from": smtp_from,
        "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"},
        "use_ssl": os.getenv("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes", "on"},
        "support_email": (os.getenv("SUPPORT_EMAIL") or smtp_from).strip(),
        "frontend_url": os.getenv("FRONTEND_URL", ""),
    }


def enviar_email_recuperacao(destinatario: str, nome: str) -> None:
    cfg = _get_smtp_config()

    logger.info(
        "SMTP config: host=%s port=%s user=%s from=%s TLS=%s SSL=%s",
        cfg["host"], cfg["port"],
        "set" if cfg["user"] else "unset",
        cfg["from"], cfg["use_tls"], cfg["use_ssl"],
    )

    if not cfg["host"] or not cfg["from"]:
        raise ValueError("Configuração de email incompleta. Verifique SMTP_HOST e SMTP_FROM.")

    mensagem = EmailMessage()
    mensagem["Subject"] = "SafeMask - Recuperação de senha"
    mensagem["From"] = cfg["from"]
    mensagem["To"] = destinatario
    if cfg["support_email"]:
        mensagem["Reply-To"] = cfg["support_email"]

    linhas = [
        f"Olá, {nome}.",
        "",
        "Recebemos uma solicitação de recuperação de senha para a sua conta SafeMask.",
        "Se foi você, responda este email ou entre em contato com o suporte para seguir com a recuperação.",
    ]
    if cfg["frontend_url"]:
        linhas.extend(["", f"Acesse o sistema em: {cfg['frontend_url']}"])
    if cfg["support_email"]:
        linhas.extend(["", f"Suporte: {cfg['support_email']}"])

    mensagem.set_content("\n".join(linhas))

    try:
        if cfg["use_ssl"]:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=20) as servidor:
                if cfg["user"]:
                    servidor.login(cfg["user"], cfg["password"] or "")
                servidor.send_message(mensagem)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as servidor:
                if cfg["use_tls"]:
                    servidor.starttls()
                if cfg["user"]:
                    servidor.login(cfg["user"], cfg["password"] or "")
                servidor.send_message(mensagem)
    except Exception:
        logger.exception(
            "Falha ao enviar email de recuperação (host=%s port=%s).",
            cfg["host"], cfg["port"],
        )
        raise