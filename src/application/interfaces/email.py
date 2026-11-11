"""Correo saliente: los casos de uso arman el mensaje y lo encolan; la infraestructura lo manda."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OutgoingEmail:
    """Correo ya renderizado (texto y HTML). Los proveedores solo lo transportan."""

    to: Sequence[str]
    subject: str
    text: str
    html: str | None = None
    # Categoría para métricas del proveedor y para los logs (nunca el destinatario).
    tag: str = "account"


class EmailDeliveryError(Exception):
    """El proveedor no aceptó el mensaje."""

    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"{provider}: {detail}")


class EmailSender(ABC):
    """Puerto de envío: Resend en producción, SMTP (Mailpit) en local, memoria en tests."""

    name: str = "email"

    @abstractmethod
    async def send(self, email: OutgoingEmail) -> None:
        """Lanza `EmailDeliveryError` si el proveedor no acepta el mensaje."""


class EmailQueue(ABC):
    """Cola de envío de la petición. Los handlers encolan después del commit: un correo nunca
    sale para un cambio que no se guardó, y la respuesta no espera al proveedor."""

    @abstractmethod
    def enqueue(self, email: OutgoingEmail) -> None: ...
