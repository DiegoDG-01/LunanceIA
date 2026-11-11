"""Avisos servidor a servidor de Sign in with Apple
(https://developer.apple.com/documentation/sign_in_with_apple/processing-changes-for-sign-in-with-apple-accounts).

- `email-disabled` / `email-enabled`: el usuario apagó o volvió a encender el reenvío de su
  correo del relay privado. No cambia nada en la cuenta: solo se registra (los correos a esa
  dirección dejarán de llegar mientras esté apagado).
- `consent-revoked`: dejó de usar su Apple ID con Lunance (Ajustes › Apple ID). Se cierran
  todas las sesiones y se borra el refresh token de Apple (ya no sirve). El vínculo se queda:
  volver a entrar con Apple pide de nuevo su consentimiento y llega el mismo `sub`.
- `account-delete`: borró su Apple ID. Además de lo anterior se quita el vínculo: ese `sub` no
  volverá. Si la cuenta no tenía otra forma de entrar, solo podrá recuperarse con "Olvidé mi
  contraseña" (si su correo no era del relay privado).

Procesar el mismo aviso dos veces no cambia nada más que repetir el evento de auditoría.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from application.auth.services.sessions import record_revocation
from application.interfaces.auth_service import SessionRevocationList
from application.interfaces.identity_providers import AppleSignInGateway
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.auth.session import RevocationReason
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.session_repository import SessionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.users.user_repository import UserRepository
from shared.exceptions.application import ProviderNotConfiguredError
from shared.utils.time import utc_now

REVOKING_EVENTS = frozenset({"consent-revoked", "account-delete"})
UNLINKING_EVENTS = frozenset({"account-delete"})


@dataclass
class AppleNotificationCommand:
    payload: str


@dataclass(frozen=True, slots=True)
class AppleNotificationResult:
    event: str
    matched: bool
    sessions_revoked: int = 0
    unlinked: bool = False


class AppleNotificationHandler:
    def __init__(
        self,
        *,
        apple: AppleSignInGateway | None,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        auth_event_repository: AuthEventRepository,
        revocations: SessionRevocationList,
        uow: AbstractUnitOfWork,
        now: Callable[[], datetime] = utc_now,
    ):
        self.apple = apple
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.auth_event_repository = auth_event_repository
        self.revocations = revocations
        self.uow = uow
        self._now = now

    async def handle(
        self, command: AppleNotificationCommand
    ) -> AppleNotificationResult:
        if self.apple is None:
            raise ProviderNotConfiguredError("Apple")
        # Lanza InvalidProviderTokenError si la firma, el emisor o la audiencia no valen.
        notification = await self.apple.notification(command.payload)
        event = notification.event
        now = self._now()
        revoked = []
        unlinked = False
        async with self.uow:
            user = await self.user_repository.get_by_apple_sub(notification.subject)
            details: dict = {"event": event, "matched": user is not None}
            if notification.notification_id:
                details["notification_id"] = notification.notification_id
            if user is not None and user.id is not None and event in REVOKING_EVENTS:
                user = await self.user_repository.get_by_id(user.id, for_update=True)
            if user is not None and user.id is not None and event in REVOKING_EVENTS:
                # Apple ya quitó la autorización: el refresh token no sirve ni para revocarla.
                await self.user_repository.set_apple_refresh_token(user.id, None)
                if event in UNLINKING_EVENTS and user.apple_sub is not None:
                    user.apple_sub = None
                    await self.user_repository.update(user)
                    unlinked = True
                    details["unlinked"] = True
                    details["remaining_methods"] = user.login_methods
                revoked = await self.session_repository.revoke_active(
                    user.id, now, RevocationReason.APPLE_REVOKED
                )
                for session in revoked:
                    await record_revocation(
                        self.auth_event_repository,
                        session,
                        now=now,
                        revoked_by="system",
                    )
                details["sessions_revoked"] = len(revoked)
            await self.auth_event_repository.record(
                AuthEvent(
                    action=AuthAction.APPLE_NOTIFICATION,
                    created_at=now,
                    user_id=user.id if user is not None else None,
                    details=details,
                )
            )
            await self.uow.commit()

        await self.revocations.revoke([session.uuid for session in revoked])
        return AppleNotificationResult(
            event=event,
            matched=user is not None,
            sessions_revoked=len(revoked),
            unlinked=unlinked,
        )
