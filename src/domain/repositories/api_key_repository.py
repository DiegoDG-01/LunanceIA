from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.api_key import APIKey


class APIKeyRepository(ABC):
    @abstractmethod
    async def create(self, api_key: APIKey) -> APIKey:
        pass

    @abstractmethod
    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        pass

    @abstractmethod
    async def list_by_user(self, user_id: int) -> List[APIKey]:
        pass

    @abstractmethod
    async def revoke(self, uuid: str, user_id: int) -> bool:
        pass

    @abstractmethod
    async def delete(self, uuid: str, user_id: int) -> bool:
        """Permanently delete an API key with ownership validation."""
        pass

    @abstractmethod
    async def touch_last_used(self, api_key_id: int) -> None:
        pass
