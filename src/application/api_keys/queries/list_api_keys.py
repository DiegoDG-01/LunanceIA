from dataclasses import dataclass

from application.dto.api_key_dto import APIKeyResponseDTO
from domain.repositories.api_key_repository import APIKeyRepository


@dataclass
class ListAPIKeysQuery:
    user_id: int


class ListAPIKeysHandler:
    def __init__(self, api_key_repository: APIKeyRepository):
        self.api_key_repository = api_key_repository

    async def handle(self, query: ListAPIKeysQuery) -> list[APIKeyResponseDTO]:
        keys = await self.api_key_repository.list_by_user(query.user_id)
        return [APIKeyResponseDTO.from_entity(key) for key in keys]