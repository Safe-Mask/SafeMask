import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", SMTP_FROM)
FRONTEND_URL = os.getenv("FRONTEND_URL", "")


def enviar_email_recuperacao(destinatario: str, nome: str) -> None:
    if not SMTP_HOST or not SMTP_FROM:
        raise ValueError("Configuração de email incompleta. Verifique SMTP_HOST e SMTP_FROM.")

    mensagem = EmailMessage()
    mensagem["Subject"] = "SafeMask - Recuperação de senha"
    mensagem["From"] = SMTP_FROM
    mensagem["To"] = destinatario
    if SUPPORT_EMAIL:
        mensagem["Reply-To"] = SUPPORT_EMAIL

    linhas = [
        f"Olá, {nome}.",
        "",
        "Recebemos uma solicitação de recuperação de senha para a sua conta SafeMask.",
        "Se foi você, responda este email ou entre em contato com o suporte para seguir com a recuperação.",
    ]

    if FRONTEND_URL:
        linhas.extend(["", f"Acesse o sistema em: {FRONTEND_URL}"])

    if SUPPORT_EMAIL:
        linhas.extend(["", f"Suporte: {SUPPORT_EMAIL}"])

    mensagem.set_content("\n".join(linhas))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as servidor:
        if SMTP_USE_TLS:
            servidor.starttls()
        if SMTP_USER:
            servidor.login(SMTP_USER, SMTP_PASSWORD or "")
        servidor.send_message(mensagem)