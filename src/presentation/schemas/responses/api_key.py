from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class APIKeyCreatedResponse(BaseModel):
    """Respuesta al crear una key. Es la única vez que se devuelve `raw_key`."""

    raw_key: str
    uuid: str
    name: str
    key_prefix: str
    scopes: list[str]
    expires_at: Optional[datetime]
    created_at: datetime


class APIKeyResponse(BaseModel):
    """Respuesta para listar keys. Nunca incluye `raw_key` ni el hash."""

    uuid: str
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime
