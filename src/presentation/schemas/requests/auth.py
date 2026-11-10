from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema para login."""

    username: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de usuario"
    )
    password: str = Field(..., min_length=8, description="Contraseña")
    device_name: str | None = Field(
        default=None,
        max_length=100,
        description="Nombre legible del dispositivo (p. ej. 'iPhone de Diego')",
    )


class RegisterRequest(BaseModel):
    """Schema para registro."""

    username: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de usuario"
    )
    password: str = Field(..., min_length=8, description="Contraseña")


class RefreshRequest(BaseModel):
    """Solo ios/android: en la web el refresh token viaja en la cookie httpOnly."""

    refresh_token: str | None = Field(default=None, max_length=200)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(
        default=None,
        max_length=200,
        description="Solo ios/android; en la web se toma de la cookie",
    )
    all_devices: bool = Field(
        default=False,
        description="Cierra también las sesiones de los demás dispositivos",
    )
