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


class ProviderTokenResponse(TokenResponse):
    """Login con Google o Apple: además del par de tokens, si la cuenta se creó (conviene
    ofrecer cambiar el username generado) o se vinculó por correo."""

    account_created: bool = Field(..., description="Cuenta nueva")
    provider_linked: bool = Field(
        ..., description="El proveedor se vinculó ahora a una cuenta existente"
    )


class LoginMethodsResponse(BaseModel):
    login_methods: list[str] = Field(
        ..., description="Formas de entrar: password, google, apple"
    )


class MessageResponse(BaseModel):
    """Respuesta genérica: misma forma exista o no el correo."""

    message: str = Field(..., description="Mensaje para mostrar al usuario")


class VerifyEmailResponse(BaseModel):
    """Cuenta creada al confirmar el correo. Para entrar hay que iniciar sesión."""

    user_uuid: str = Field(..., description="UUID del usuario")
    username: str = Field(..., description="Nombre del usuario")
    email: str = Field(..., description="Correo confirmado")
    message: str = Field(..., description="Mensaje de confirmación")


class UserInfoResponse(BaseModel):
    """Schema de respuesta para información del usuario."""

    user_uuid: str = Field(..., description="UUID del usuario")
    username: str = Field(..., description="Nombre del usuario")
    email: str | None = Field(..., description="Correo de la cuenta")
    email_verified: bool = Field(..., description="Si el correo está confirmado")
    is_active: bool = Field(..., description="Estado del usuario")
    login_methods: list[str] = Field(
        default_factory=list, description="Formas de entrar: password, google, apple"
    )


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
