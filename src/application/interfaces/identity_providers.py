"""Puertos para entrar con Google y Apple: verificación de ID tokens, canje del código de
Apple, tokens de un solo uso y cifrado del refresh token de Apple."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class IdentityProvider(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"

    @property
    def label(self) -> str:
        return "Google" if self is IdentityProvider.GOOGLE else "Apple"


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    """Cuenta del proveedor ya comprobada: firma, emisor, audiencia, caducidad y nonce."""

    provider: IdentityProvider
    subject: str
    # Audiencia del token (el client ID con el que la app lo pidió): con Apple, el código de
    # autorización se canjea con ese mismo client ID.
    audience: str
    expires_at: datetime
    # Solo si el proveedor lo marca como verificado; None si no lo trae.
    email: str | None = None
    name: str | None = None
    # Google: dominio de Google Workspace (claim `hd`). Con él, Google administra el buzón.
    hosted_domain: str | None = None
    # Apple: dirección del relay privado (`…@privaterelay.appleid.com`).
    private_email: bool = False


@dataclass(frozen=True, slots=True)
class AppleNotification:
    """Aviso servidor a servidor de Apple, ya comprobado (firma, emisor y audiencia)."""

    # `email-disabled`, `email-enabled`, `consent-revoked` o `account-delete`.
    event: str
    subject: str
    # `jti` del JWT: identifica el aviso para no procesarlo dos veces.
    notification_id: str | None = None
    event_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class AppleTokens:
    """Lo que devuelve Apple al canjear el código de autorización."""

    refresh_token: str
    # Client ID con el que se canjeó: la revocación debe usar el mismo.
    client_id: str
    # `sub` del id_token que acompaña la respuesta (si viene).
    subject: str | None = None


class GoogleTokenVerifier(ABC):
    @abstractmethod
    async def verify(self, id_token: str, *, nonce: str | None) -> ProviderIdentity:
        """La identidad del ID token. Lanza `InvalidProviderTokenError` si no es válido (con
        el motivo, que solo va a la auditoría) e `IdentityProviderUnavailableError` si no se
        pueden obtener las claves de Google."""


class AppleSignInGateway(ABC):
    """Sign in with Apple: identity token, canje del código, revocación y avisos."""

    @property
    @abstractmethod
    def can_exchange_codes(self) -> bool:
        """False sin la clave .p8: no se puede firmar el client secret."""

    @abstractmethod
    async def verify(
        self, identity_token: str, *, nonce: str | None
    ) -> ProviderIdentity:
        """Como `GoogleTokenVerifier.verify`, con las claves de Apple."""

    @abstractmethod
    async def exchange_code(
        self, authorization_code: str, *, client_id: str
    ) -> AppleTokens | None:
        """Canjea el código por un refresh token. None si Apple lo rechaza (usado, caducado
        o de otra app). Lanza `IdentityProviderUnavailableError` si Apple no responde."""

    @abstractmethod
    async def revoke(self, refresh_token: str, *, client_id: str) -> None:
        """Quita la autorización de Lunance en la cuenta de Apple. Lanza
        `IdentityProviderUnavailableError` si Apple no responde."""

    @abstractmethod
    async def notification(self, payload: str) -> AppleNotification:
        """El aviso del JWT que Apple manda a la URL de notificaciones. Lanza
        `InvalidProviderTokenError` si no es válido."""


class UsedProviderTokens(ABC):
    """ID tokens de Google y Apple ya usados: cada uno abre una sola sesión."""

    @abstractmethod
    async def claim(self, token: str, *, expires_at: datetime) -> bool:
        """True la primera vez que se usa `token`; False si ya se usó. Si el almacén no
        responde lanza `ServiceTemporarilyUnavailableError`: nunca se acepta un token sin
        poder marcarlo."""


class SecretCipher(ABC):
    """Cifrado simétrico autenticado para secretos guardados en la base."""

    @abstractmethod
    def encrypt(self, plaintext: str, *, context: str) -> str:
        """`context` (p. ej. el id del usuario) queda atado al texto cifrado: copiado a otra
        fila deja de descifrarse."""

    @abstractmethod
    def decrypt(self, ciphertext: str, *, context: str) -> str:
        """Lanza `ValueError` si el texto no se descifra con la clave y el contexto."""
