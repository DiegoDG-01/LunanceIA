import hashlib
import secrets
from dataclasses import dataclass

from application.dto.api_key_dto import APICreatedResponseDTO, CreateAPIKeyDTO
from domain.entities.api_key import APIKey
from domain.repositories.api_key_repository import APIKeyRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork


@dataclass
class CreateAPIKeyCommand:
    dto: CreateAPIKeyDTO


class CreateAPIKeyHandler:
    def __init__(
        self,
        api_key_repository: APIKeyRepository,
        uow: AbstractUnitOfWork,
    ):
        self.api_key_repository = api_key_repository
        self.uow = uow

    async def handle(self, command: CreateAPIKeyCommand) -> APICreatedResponseDTO:
        dto = command.dto

        raw_key = f"moon_{secrets.token_urlsafe(32)}"
        key_prefix = raw_key[:12]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        entity = APIKey(
            user_id=dto.user_id,
            name=dto.name,
            key_prefix=key_prefix,
            scopes=dto.scopes,
            expires_at=dto.expires_at,
            key_hash=key_hash,
        )

        async with self.uow:
            created = await self.api_key_repository.create(entity)
            await self.uow.commit()

        return APICreatedResponseDTO.from_entity(created, raw_key=raw_key)
