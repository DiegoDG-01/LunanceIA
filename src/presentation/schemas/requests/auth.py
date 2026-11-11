from pydantic import BaseModel, EmailStr, Field

# Tope de longitud de las contraseñas: Argon2 acepta cualquiera, pero no hace falta que nadie
# pueda mandar megas para que los hasheemos.
PASSWORD_MAX_LENGTH = 256
# RFC 5321: 254 caracteres como máximo para una dirección.
EMAIL_MAX_LENGTH = 254


class LoginRequest(BaseModel):
    """Schema para login."""

    email: EmailStr = Field(..., max_length=EMAIL_MAX_LENGTH, description="Correo")
    password: str = Field(
        ..., min_length=8, max_length=PASSWORD_MAX_LENGTH, description="Contraseña"
    )
    device_name: str | None = Field(
        default=None,
        max_length=100,
        description="Nombre legible del dispositivo (p. ej. 'iPhone de Diego')",
    )


class RegisterRequest(BaseModel):
    """Registro con correo. La cuenta se crea al abrir el enlace del correo."""

    email: EmailStr = Field(..., max_length=EMAIL_MAX_LENGTH, description="Correo")
    username: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de usuario (único)"
    )
    password: str = Field(
        ..., min_length=8, max_length=PASSWORD_MAX_LENGTH, description="Contraseña"
    )


class VerifyEmailRequest(BaseModel):
    token: str = Field(
        ..., min_length=1, max_length=200, description="Token del enlace del correo"
    )


class EmailRequest(BaseModel):
    """Reenvío de verificación y "Olvidé mi contraseña"."""

    email: EmailStr = Field(..., max_length=EMAIL_MAX_LENGTH, description="Correo")


class ResetPasswordRequest(BaseModel):
    token: str = Field(
        ..., min_length=1, max_length=200, description="Token del enlace del correo"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=PASSWORD_MAX_LENGTH,
        description="Contraseña nueva",
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        ...,
        min_length=1,
        max_length=PASSWORD_MAX_LENGTH,
        description="Contraseña actual",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=PASSWORD_MAX_LENGTH,
        description="Contraseña nueva",
    )


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


# Un ID token real mide 1-2 KB; el tope solo evita cuerpos enormes.
ID_TOKEN_MAX_LENGTH = 8192
NONCE_MAX_LENGTH = 512


class ProviderTokenRequest(BaseModel):
    """ID token de Google o Apple tal como lo entregó su SDK."""

    id_token: str = Field(
        ...,
        min_length=1,
        max_length=ID_TOKEN_MAX_LENGTH,
        description="ID token (JWT) que la app obtuvo del proveedor",
    )
    nonce: str | None = Field(
        default=None,
        min_length=1,
        max_length=NONCE_MAX_LENGTH,
        description=(
            "Nonce en claro. Al proveedor se le manda su SHA-256 (hex); obligatorio si el "
            "token lleva `nonce`"
        ),
    )


class GoogleSignInRequest(ProviderTokenRequest):
    device_name: str | None = Field(
        default=None, max_length=100, description="Nombre legible del dispositivo"
    )


class AppleTokenRequest(ProviderTokenRequest):
    authorization_code: str | None = Field(
        default=None,
        min_length=1,
        max_length=1024,
        description=(
            "Código de autorización de Apple: se canjea por el refresh token que permite "
            "revocar el acceso al borrar la cuenta"
        ),
    )


_CURRENT_PASSWORD_DESCRIPTION = (
    "Contraseña actual; obligatoria si la cuenta tiene una. Sin contraseña, la sesión debe "
    "haberse iniciado hace menos de 10 minutos"
)


class LinkGoogleRequest(ProviderTokenRequest):
    current_password: str | None = Field(
        default=None,
        max_length=PASSWORD_MAX_LENGTH,
        description=_CURRENT_PASSWORD_DESCRIPTION,
    )


class LinkAppleRequest(AppleTokenRequest):
    current_password: str | None = Field(
        default=None,
        max_length=PASSWORD_MAX_LENGTH,
        description=_CURRENT_PASSWORD_DESCRIPTION,
    )


class AppleSignInRequest(AppleTokenRequest):
    name: str | None = Field(
        default=None,
        max_length=100,
        description="Nombre completo; Apple solo lo da la primera vez que se autoriza",
    )
    device_name: str | None = Field(
        default=None, max_length=100, description="Nombre legible del dispositivo"
    )


class AppleNotificationRequest(BaseModel):
    """Cuerpo que manda Apple a la URL de notificaciones servidor a servidor."""

    payload: str = Field(..., min_length=1, max_length=16384)


class UpdateMeRequest(BaseModel):
    username: str = Field(
        ..., min_length=1, max_length=100, description="Nombre de usuario (único)"
    )
