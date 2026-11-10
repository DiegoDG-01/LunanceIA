from datetime import datetime

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Schema de respuesta para tokens.

    `refresh_token` solo viene en ios/android; en la web va en una cookie httpOnly.
    """

    access_token: str = Field(..., description="Access token")
    token_type: str = Field(default="bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Segundos de vida del access token")
    refresh_token: str | None = Field(
        default=None, description="Refresh token (solo ios/android)"
    )


class RegisterResponse(BaseModel):
    """Schema de respuesta para registro."""

    user_uuid: str = Field(..., description="UUID del usuario")
    username: str = Field(..., description="Nombre del usuario")
    message: str = Field(..., description="Mensaje de confirmación")


class UserInfoResponse(BaseModel):
    """Schema de respuesta para información del usuario."""

    user_uuid: str = Field(..., description="UUID del usuario")
    username: str = Field(..., description="Nombre del usuario")
    is_active: bool = Field(..., description="Estado del usuario")


class SessionResponse(BaseModel):
    """Una sesión abierta del usuario (un dispositivo)."""

    uuid: str
    platform: str
    device_name: str | None
    client: str | None
    created_at: datetime
    last_seen_at: datetime
    last_ip: str | None
    is_current: bool


class LogoutResponse(BaseModel):
    message: str = "Logout exitoso"
