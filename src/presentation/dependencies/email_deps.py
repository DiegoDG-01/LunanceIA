"""Correo saliente de la petición: se manda con `BackgroundTasks`, después de responder."""

from functools import lru_cache

from fastapi import BackgroundTasks, Depends

from application.interfaces.email import EmailQueue, EmailSender, OutgoingEmail
from infrastructure.config.settings import settings
from infrastructure.external_services.email.delivery import deliver
from infrastructure.external_services.email.factory import build_email_sender


@lru_cache
def get_email_sender() -> EmailSender:
    return build_email_sender(settings)


class BackgroundEmailQueue(EmailQueue):
    """Cada correo encolado se manda cuando la respuesta ya salió: el cliente no espera al
    proveedor y un fallo de envío solo queda en el log."""

    def __init__(self, tasks: BackgroundTasks, sender: EmailSender):
        self._tasks = tasks
        self._sender = sender

    def enqueue(self, email: OutgoingEmail) -> None:
        self._tasks.add_task(deliver, self._sender, email)


def get_email_queue(
    background_tasks: BackgroundTasks,
    sender: EmailSender = Depends(get_email_sender),
) -> EmailQueue:
    return BackgroundEmailQueue(background_tasks, sender)
