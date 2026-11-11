from application.interfaces.email import EmailSender
from infrastructure.config.settings import Settings
from infrastructure.external_services.email.memory import InMemoryEmailSender
from infrastructure.external_services.email.resend import ResendEmailSender
from infrastructure.external_services.email.smtp import SmtpEmailSender


def build_email_sender(settings: Settings) -> EmailSender:
    """El backend sale de `EMAIL_BACKEND` (ya validado en `Settings`)."""
    backend = settings.email_backend
    if backend == "resend":
        return ResendEmailSender(
            api_key=settings.RESEND_API_KEY.get_secret_value(),
            sender=settings.EMAIL_FROM,
        )
    if backend == "smtp":
        return SmtpEmailSender(
            sender=settings.EMAIL_FROM,
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD.get_secret_value(),
            starttls=settings.SMTP_STARTTLS,
        )
    return InMemoryEmailSender()
