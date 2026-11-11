from application.interfaces.email import EmailSender, OutgoingEmail


class InMemoryEmailSender(EmailSender):
    """Guarda los correos en `outbox` en vez de mandarlos (tests y `EMAIL_BACKEND=memory`)."""

    name = "memory"

    def __init__(self) -> None:
        self.outbox: list[OutgoingEmail] = []

    async def send(self, email: OutgoingEmail) -> None:
        self.outbox.append(email)

    def sent_to(self, address: str) -> list[OutgoingEmail]:
        return [email for email in self.outbox if address in email.to]

    def clear(self) -> None:
        self.outbox.clear()
