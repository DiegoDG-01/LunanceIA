from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema para login."""

    username: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de usuario"
    )
    password: str = Field(
        ..., min_length=8, description="Contraseña"
    )


class RegisterRequest(BaseModel):
    """Schema para registro."""

    username: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de usuario"
    )
    password: str = Field(
        ..., min_length=8, description="Contraseña"
    )


class RefreshTokenRequest(BaseModel):
    """Schema para refresh token."""

    refresh_token: str = Field(..., description="Refresh token")
