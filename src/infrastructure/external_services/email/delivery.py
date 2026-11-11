import logging

from application.interfaces.email import EmailSender, OutgoingEmail

logger = logging.getLogger(__name__)


async def deliver(sender: EmailSender, email: OutgoingEmail) -> None:
    """Envío en segundo plano (después de responder): un fallo del proveedor se registra en
    el log y no llega al cliente. El log nunca lleva el destinatario ni el contenido."""
    try:
        await sender.send(email)
    except Exception:
        logger.exception(
            "Email delivery failed",
            extra={"email_provider": sender.name, "email_tag": email.tag},
        )
    else:
        logger.info(
            "Email sent",
            extra={"email_provider": sender.name, "email_tag": email.tag},
        )
