import hashlib
from datetime import UTC, datetime

from domain.entities.user import User
from domain.repositories.api_key_repository import APIKeyRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from shared.exceptions.base import UnauthorizedError


class APIKeyService:
    def __init__(
        self,
        api_key_repository: APIKeyRepository,
        user_repository: UserRepository,
        uow: AbstractUnitOfWork,
    ):
        self.api_key_repository = api_key_repository
        self.user_repository = user_repository
        self.uow = uow

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    async def authenticate(self, raw_key: str) -> tuple[User, list[str]]:
        key_hash = self.hash_key(raw_key)

        api_key = await self.api_key_repository.get_by_hash(key_hash)
        if api_key is None or not api_key.is_valid():
            raise UnauthorizedError("Invalid or expired API key")

        user = await self.user_repository.get_by_id(api_key.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("API key owner not found or inactive")

        now = datetime.now(UTC)
        last_used = api_key.last_used_at
        if last_used is not None and last_used.tzinfo is None:
            last_used = last_used.replace(tzinfo=UTC)

        if last_used is None or (now - last_used).total_seconds() > 60:
            async with self.uow:
                await self.api_key_repository.touch_last_used(api_key.id)
                await self.uow.commit()

        return user, api_key.scopes
