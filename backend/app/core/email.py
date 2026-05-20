import os
import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)


def enviar_email_recuperacao(destinatario: str, nome: str) -> None:
    api_key = os.getenv("BREVO_API_KEY")
    smtp_from = os.getenv("SMTP_FROM")
    smtp_from_name = os.getenv("SMTP_FROM_NAME", "SafeMask")
    support_email = os.getenv("SUPPORT_EMAIL") or smtp_from
    frontend_url = os.getenv("FRONTEND_URL", "")

    if not api_key:
        raise ValueError("BREVO_API_KEY não configurado.")
    if not smtp_from:
        raise ValueError("SMTP_FROM não configurado.")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    linhas = [
        f"Olá, {nome}.",
        "",
        "Recebemos uma solicitação de recuperação de senha para a sua conta SafeMask.",
        "Se foi você, responda este email ou entre em contato com o suporte para seguir com a recuperação.",
    ]
    if frontend_url:
        linhas.extend(["", f"Acesse o sistema em: {frontend_url}"])
    if support_email:
        linhas.extend(["", f"Suporte: {support_email}"])

    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": destinatario}],
        sender={"email": smtp_from, "name": smtp_from_name},
        reply_to={"email": support_email},
        subject="SafeMask - Recuperação de senha",
        text_content="\n".join(linhas),
    )

    try:
        api_instance.send_transac_email(email)
        logger.info("Email de recuperação enviado para %s", destinatario)
    except ApiException:
        logger.exception("Falha ao enviar email via Brevo para %s", destinatario)
        raise