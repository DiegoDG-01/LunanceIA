"""Cuenta de Lunance a partir de una identidad de Google o Apple ya verificada.

Tres casos:

- La identidad ya está vinculada (`google_sub`/`apple_sub`): esa cuenta.
- Hay una cuenta con ese correo: se vincula solo si el buzón sigue siendo de quien lo verificó
  con el proveedor. Eso pasa con los buzones que el propio proveedor administra y nunca
  reasigna (Gmail para Google; iCloud, me.com, mac.com y el relay privado para Apple) o, con
  Google, cuando el correo es del dominio de Google Workspace de la cuenta (claim `hd`). Con
  cualquier otro dominio el proveedor solo comprobó el correo al crear su cuenta y el buzón
  pudo cambiar de manos (un exempleado, un dominio caducado): se pide entrar con el método de
  siempre y vincular desde ajustes (`ProviderLinkRequiredError`).
- No hay cuenta: se crea ya verificada, sin contraseña y con un username generado a partir del
  nombre (o del correo), único y que se puede cambiar después. Un registro pendiente con ese
  correo se descarta: su enlace deja de valer y su username queda libre.
"""

import re
import secrets
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from application.interfaces.identity_providers import (
    IdentityProvider,
    ProviderIdentity,
)
from domain.entities.users.user import User
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import InvalidProviderTokenError
from shared.exceptions.domain import (
    ProviderAccountConflictError,
    ProviderLinkRequiredError,
)
from shared.utils.emails import normalize_email

# Buzones que el proveedor administra y nunca reasigna a otra persona.
STABLE_MAILBOX_DOMAINS: dict[IdentityProvider, frozenset[str]] = {
    IdentityProvider.GOOGLE: frozenset({"gmail.com", "googlemail.com"}),
    IdentityProvider.APPLE: frozenset(
        {"icloud.com", "me.com", "mac.com", "privaterelay.appleid.com"}
    ),
}

DEFAULT_USERNAME_BASE = "usuario"
USERNAME_MIN_LENGTH = 3
USERNAME_BASE_LENGTH = 20
USERNAME_ATTEMPTS = 10
_NOT_USERNAME = re.compile(r"[^a-z0-9._]")


class ConcurrentSignInError(Exception):
    """Otra petición creó o vinculó la misma cuenta a la vez: reintentar la encuentra."""


@dataclass(frozen=True, slots=True)
class ExternalAccount:
    user: User
    created: bool = False
    linked: bool = False


def linked_subject(user: User, provider: IdentityProvider) -> str | None:
    return user.google_sub if provider is IdentityProvider.GOOGLE else user.apple_sub


def set_subject(user: User, provider: IdentityProvider, subject: str | None) -> None:
    if provider is IdentityProvider.GOOGLE:
        user.google_sub = subject
    else:
        user.apple_sub = subject


def owner_confirmed(identity: ProviderIdentity, email: str) -> bool:
    """Si el correo sigue siendo de quien lo verificó con el proveedor
    (https://developers.google.com/identity/openid-connect/openid-connect#an-id-tokens-payload)."""
    domain = email.rsplit("@", 1)[-1]
    if domain in STABLE_MAILBOX_DOMAINS[identity.provider]:
        return True
    return (
        identity.provider is IdentityProvider.GOOGLE
        and identity.hosted_domain is not None
        and domain == identity.hosted_domain
    )


def username_base(name: str | None, email: str | None = None) -> str:
    """De "María José" sale "mariajose": minúsculas sin acentos, empezando por letra. Sin
    nombre útil se usa la parte local del correo y, si tampoco sirve, "usuario"."""
    for source in (name, (email or "").split("@", 1)[0]):
        ascii_text = (
            unicodedata.normalize("NFKD", source or "")
            .encode("ascii", "ignore")
            .decode()
        )
        base = _NOT_USERNAME.sub("", ascii_text.lower()).lstrip("0123456789._")
        base = base[:USERNAME_BASE_LENGTH].rstrip("._")
        if len(base) >= USERNAME_MIN_LENGTH:
            return base
    return DEFAULT_USERNAME_BASE


class ExternalAccounts:
    """Encuentra, vincula o crea la cuenta. Nunca hace commit: lo hace el handler."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        pending_signup_repository: PendingSignupRepository,
        username_suffix: Callable[[], str] = lambda: f"{secrets.randbelow(10_000):04d}",
    ) -> None:
        self.users = user_repository
        self.pending = pending_signup_repository
        self._username_suffix = username_suffix

    async def linked_user(self, identity: ProviderIdentity) -> User | None:
        if identity.provider is IdentityProvider.GOOGLE:
            return await self.users.get_by_google_sub(identity.subject)
        return await self.users.get_by_apple_sub(identity.subject)

    async def resolve(
        self, identity: ProviderIdentity, *, name: str | None, now: datetime
    ) -> ExternalAccount:
        user = await self.linked_user(identity)
        if user is not None:
            return ExternalAccount(user=user)

        email = normalize_email(identity.email or "")
        if not email:
            # Sin correo verificado no se puede vincular ni crear la cuenta.
            raise InvalidProviderTokenError(identity.provider.value, "email_missing")

        user = await self.users.get_by_email(email)
        if user is None:
            return ExternalAccount(
                user=await self._create(identity, email, name or identity.name, now),
                created=True,
            )

        if linked_subject(user, identity.provider) is not None:
            # La cuenta ya tiene otra cuenta del mismo proveedor (cuyo correo cambió y ahora
            # usa otra persona en el proveedor): no se sustituye.
            raise ProviderAccountConflictError(identity.provider.label)
        if not owner_confirmed(identity, email):
            raise ProviderLinkRequiredError(identity.provider.label, user.login_methods)
        set_subject(user, identity.provider, identity.subject)
        user.email_verified = True
        try:
            user = await self.users.update(user)
        except IntegrityError as error:
            raise ConcurrentSignInError from error
        return ExternalAccount(user=user, linked=True)

    async def _create(
        self, identity: ProviderIdentity, email: str, name: str | None, now: datetime
    ) -> User:
        signup = await self.pending.get_by_email(email, for_update=True)
        if signup is not None and signup.id is not None:
            # El correo ya está verificado por el proveedor: el registro pendiente sobra.
            await self.pending.delete(signup.id)

        user = User.create_external_user(
            name=await self.free_username(name, email, now),
            email=email,
            google_sub=identity.subject
            if identity.provider is IdentityProvider.GOOGLE
            else None,
            apple_sub=identity.subject
            if identity.provider is IdentityProvider.APPLE
            else None,
        )
        user.registration_date = now
        user.last_login = now
        try:
            return await self.users.create(user)
        except IntegrityError as error:
            raise ConcurrentSignInError from error

    async def free_username(
        self, name: str | None, email: str | None, now: datetime
    ) -> str:
        for candidate in self._username_candidates(name, email):
            if await self.username_taken(candidate, now):
                continue
            return candidate
        # Diez intentos ocupados: casi imposible; otro intento de entrar lo resuelve.
        raise ConcurrentSignInError

    async def username_taken(
        self, username: str, now: datetime, *, email: str | None = None
    ) -> bool:
        """Ocupado por una cuenta o reservado por un registro pendiente abierto (de otro
        correo)."""
        if await self.users.get_by_username(username) is not None:
            return True
        holder = await self.pending.get_by_username(username)
        return holder is not None and holder.email != email and holder.is_open(now)

    def _username_candidates(
        self, name: str | None, email: str | None
    ) -> Iterator[str]:
        base = username_base(name, email)
        yield base
        for _ in range(USERNAME_ATTEMPTS - 1):
            yield f"{base}_{self._username_suffix()}"
