from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from domain.entities.api_key import APIKey


@dataclass
class CreateAPIKeyDTO:
    user_id: int
    name: str
    scopes: list[str]
    expires_at: Optional[datetime] = None


@dataclass
class APICreatedResponseDTO:
    raw_key: str
    uuid: str
    name: str
    key_prefix: str
    scopes: list[str]
    expires_at: Optional[datetime]
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: APIKey, raw_key: str) -> "APICreatedResponseDTO":
        return cls(
            raw_key=raw_key,
            uuid=entity.uuid,
            name=entity.name,
            key_prefix=entity.key_prefix,
            scopes=entity.scopes,
            expires_at=entity.expires_at,
            created_at=entity.created_at,
        )

@dataclass
class APIKeyResponseDTO:
    uuid: str
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: APIKey) -> "APIKeyResponseDTO":
        return cls(
            uuid=entity.uuid,
            name=entity.name,
            key_prefix=entity.key_prefix,
            scopes=entity.scopes,
            is_active=entity.is_active,
            expires_at=entity.expires_at,
            last_used_at=entity.last_used_at,
            created_at=entity.created_at,
        )
