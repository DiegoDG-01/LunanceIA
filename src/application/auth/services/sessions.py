from datetime import datetime
from typing import cast

from application.auth.config import AuthConfig
from application.auth.dto import ClientContext, IssuedSession
from application.interfaces.auth_service import AccessTokenIssuer
from domain.entities.auth.auth_event import AuthAction, AuthEvent
from domain.entities.auth.refresh_token import RefreshToken
from domain.entities.auth.session import RevocationReason, UserSession
from domain.repositories.auth.auth_event_repository import AuthEventRepository
from domain.repositories.auth.refresh_token_repository import RefreshTokenRepository
from domain.repositories.auth.session_repository import SessionRepository
from shared.utils.tokens import REFRESH_TOKEN_PREFIX, generate_token, hash_token


class SessionManager:
    """Abre sesiones y emite el par access + refresh. No hace commit: lo hace el handler."""

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        auth_event_repository: AuthEventRepository,
        token_issuer: AccessTokenIssuer,
        config: AuthConfig,
    ):
        self.session_repository = session_repository
        self.refresh_token_repository = refresh_token_repository
        self.auth_event_repository = auth_event_repository
        self.token_issuer = token_issuer
        self.config = config

    async def open(
        self, *, user_id: int, user_uuid: str, context: ClientContext, now: datetime
    ) -> tuple[IssuedSession, list[UserSession]]:
        """Abre la sesión del dispositivo y devuelve también las que sustituyó.

        Una sesión por dispositivo: volver a entrar desde el mismo revoca solo la anterior de
        ese dispositivo. Quien llama debe pasar las sustituidas a la lista de revocadas después
        del commit.
        """
        if context.device_id is None:
            raise ValueError("Una sesión necesita el id del dispositivo")
        replaced = await self.session_repository.revoke_active(
            user_id, now, RevocationReason.REPLACED, device_id=context.device_id
        )
        for old in replaced:
            await record_revocation(
                self.auth_event_repository,
                old,
                now=now,
                revoked_by="system",
                context=context,
            )

        session = UserSession.open(
            user_id=user_id,
            device_id=context.device_id,
            platform=context.platform,
            lifetime=self.config.lifetime_for(context.platform),
            now=now,
            ip=context.ip,
            device_name=context.device_name,
            client=context.client,
            user_agent=context.user_agent,
        )
        session = await self.session_repository.add(session)
        issued = await self.issue(session, user_uuid=user_uuid, now=now)
        return issued, replaced

    async def issue(
        self,
        session: UserSession,
        *,
        user_uuid: str,
        now: datetime,
        refresh_token: str | None = None,
    ) -> IssuedSession:
        refresh_token = refresh_token or generate_token(REFRESH_TOKEN_PREFIX)
        await self.refresh_token_repository.add(
            RefreshToken(
                token_hash=hash_token(refresh_token),
                session_id=cast(int, session.id),
                created_at=now,
            )
        )
        return self.access_pair(
            session, user_uuid=user_uuid, refresh_token=refresh_token
        )

    def access_pair(
        self, session: UserSession, *, user_uuid: str, refresh_token: str
    ) -> IssuedSession:
        """Emite el access sin crear otro refresh: sirve también para reintentos de rotación."""
        access = self.token_issuer.issue(user_uuid=user_uuid, session_uuid=session.uuid)
        return IssuedSession(
            session=session,
            access_token=access.token,
            refresh_token=refresh_token,
            expires_in=access.expires_in,
        )


async def record_revocation(
    events: AuthEventRepository,
    session: UserSession,
    *,
    now: datetime,
    revoked_by: str,
    context: ClientContext | None = None,
    actor_session_uuid: str | None = None,
) -> None:
    """`session.revoked` con el motivo y quién la cerró (`user` o `system`)."""
    details: dict[str, str] = {
        "session_uuid": session.uuid,
        "reason": session.revoked_reason.value if session.revoked_reason else "",
        "revoked_by": revoked_by,
    }
    if actor_session_uuid:
        details["actor_session_uuid"] = actor_session_uuid
    await events.record(
        AuthEvent(
            action=AuthAction.SESSION_REVOKED,
            created_at=now,
            user_id=session.user_id,
            session_id=session.id,
            ip=context.ip if context else None,
            user_agent=context.user_agent if context else None,
            details=details,
        )
    )
