import asyncio
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from application.interfaces.email import EmailDeliveryError, EmailSender, OutgoingEmail


class SmtpEmailSender(EmailSender):
    """SMTP genérico. En local apunta a Mailpit (UI en http://localhost:8025).

    `smtplib` es síncrono: cada envío corre en un hilo para no bloquear el event loop.
    """

    name = "smtp"

    def __init__(
        self,
        *,
        sender: str,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        starttls: bool = False,
        timeout: float = 10.0,
    ) -> None:
        self._sender = sender
        self._host = host
        self._port = port
        self._username = username or None
        self._password = password or None
        self._starttls = starttls
        self._timeout = timeout

    def build_message(self, email: OutgoingEmail) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = ", ".join(email.to)
        message["Subject"] = email.subject
        message["Date"] = formatdate(localtime=False)
        message["Message-ID"] = make_msgid(domain="lunance")
        message["X-Lunance-Tag"] = email.tag
        message.set_content(email.text)
        if email.html:
            message.add_alternative(email.html, subtype="html")
        return message

    def _send_sync(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
            if self._starttls:
                smtp.starttls()
            if self._username and self._password:
                smtp.login(self._username, self._password)
            smtp.send_message(message)

    async def send(self, email: OutgoingEmail) -> None:
        try:
            await asyncio.to_thread(self._send_sync, self.build_message(email))
        except (smtplib.SMTPException, OSError) as error:
            raise EmailDeliveryError(self.name, type(error).__name__) from error
