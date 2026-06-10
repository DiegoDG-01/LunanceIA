from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from domain.objects.enums import APIKeyScope


class CreateAPIKeyRequest(BaseModel):
    """Schema para crear una API key."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre identificador de la key"
    )
    scopes: list[APIKeyScope] = Field(
        ..., min_length=1, description="Permisos de la key (solo valores del enum)"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Fecha de expiración (opcional, null = no expira)"
    )
