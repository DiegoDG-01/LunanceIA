from datetime import datetime
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.auth.pending_signup import EmailVerificationToken, PendingSignup
from domain.repositories.auth.pending_signup_repository import PendingSignupRepository
from infrastructure.database.models.pending_signup import (
    EmailVerificationTokenModel,
    PendingSignupModel,
)
from shared.utils.time import as_utc


class SQLAlchemyPendingSignupRepository(PendingSignupRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _to_entity(model: PendingSignupModel) -> PendingSignup:
        return PendingSignup(
            id=model.id,
            email=model.email,
            username=model.username,
            password_hash=model.password_hash,
            created_at=as_utc(model.created_at),
            expires_at=as_utc(model.expires_at),
        )

    async def _one(self, stmt, for_update: bool) -> PendingSignup | None:
        if for_update:
            stmt = stmt.with_for_update()
        stmt = stmt.execution_options(populate_existing=True)
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(
        self, email: str, *, for_update: bool = False
    ) -> PendingSignup | None:
        stmt = select(PendingSignupModel).where(PendingSignupModel.email == email)
        return await self._one(stmt, for_update)

    async def get_by_username(self, username: str) -> PendingSignup | None:
        stmt = select(PendingSignupModel).where(PendingSignupModel.username == username)
        return await self._one(stmt, False)

    async def get(
        self, signup_id: int, *, for_update: bool = False
    ) -> PendingSignup | None:
        stmt = select(PendingSignupModel).where(PendingSignupModel.id == signup_id)
        return await self._one(stmt, for_update)

    async def add(self, signup: PendingSignup) -> PendingSignup:
        model = PendingSignupModel(
            email=signup.email,
            username=signup.username,
            password_hash=signup.password_hash,
            created_at=signup.created_at,
            expires_at=signup.expires_at,
        )
        self.db.add(model)
        await self.db.flush()
        signup.id = model.id
        return signup

    async def save(self, signup: PendingSignup) -> None:
        model = await self.db.get(PendingSignupModel, signup.id)
        if model is None:
            return
        model.email = signup.email
        model.username = signup.username
        model.password_hash = signup.password_hash
        model.created_at = signup.created_at
        model.expires_at = signup.expires_at
        await self.db.flush()

    async def delete(self, signup_id: int) -> None:
        # La FK borra los enlaces en cascada; se hace explícito para no depender de ella.
        await self.delete_tokens(signup_id)
        await self.db.execute(
            delete(PendingSignupModel).where(PendingSignupModel.id == signup_id)
        )

    async def add_token(self, token: EmailVerificationToken) -> None:
        self.db.add(
            EmailVerificationTokenModel(
                token_hash=token.token_hash,
                pending_signup_id=token.pending_signup_id,
                created_at=token.created_at,
                expires_at=token.expires_at,
            )
        )
        await self.db.flush()

    async def get_token(self, token_hash: str) -> EmailVerificationToken | None:
        model = await self.db.get(EmailVerificationTokenModel, token_hash)
        if model is None:
            return None
        return EmailVerificationToken(
            token_hash=model.token_hash,
            pending_signup_id=model.pending_signup_id,
            created_at=as_utc(model.created_at),
            expires_at=as_utc(model.expires_at),
        )

    async def delete_tokens(self, signup_id: int) -> None:
        await self.db.execute(
            delete(EmailVerificationTokenModel).where(
                EmailVerificationTokenModel.pending_signup_id == signup_id
            )
        )

    async def purge(self, *, expired_before: datetime) -> int:
        expired = PendingSignupModel.expires_at < expired_before
        await self.db.execute(
            delete(EmailVerificationTokenModel).where(
                EmailVerificationTokenModel.pending_signup_id.in_(
                    select(PendingSignupModel.id).where(expired)
                )
            )
        )
        result = cast(
            CursorResult,
            await self.db.execute(delete(PendingSignupModel).where(expired)),
        )
        return result.rowcount or 0
