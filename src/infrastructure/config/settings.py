from typing import Any, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings

EMAIL_BACKENDS = ("resend", "smtp", "memory")
# Sin EMAIL_BACKEND explícito: cada entorno usa el suyo.
DEFAULT_EMAIL_BACKEND = {"PROD": "resend", "DEV": "smtp", "TEST": "memory"}


class Settings(BaseSettings):
    # Access token: JWT EdDSA (Ed25519). Claves PEM; en .env se aceptan en una línea con "\n".
    # Cómo generarlas: README, «Configurar variables de entorno».
    JWT_PRIVATE_KEY: SecretStr
    JWT_PUBLIC_KEY: str
    JWT_ISSUER: str = "lunance"
    JWT_AUDIENCE: str = "lunance-api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10

    # Refresh token opaco: esta clave deriva el único sucesor de cada token al rotarlo.
    REFRESH_ROTATION_KEY: SecretStr = Field(min_length=32)
    # Repetir un refresh ya canjeado dentro de esta ventana no revoca la sesión.
    REFRESH_REUSE_GRACE_SECONDS: int = 30
    # Duración de las sesiones: inactividad máxima y tope absoluto desde el login.
    SESSION_WEB_IDLE_DAYS: int = 1
    SESSION_WEB_ABSOLUTE_DAYS: int = 7
    SESSION_MOBILE_IDLE_DAYS: int = 30
    SESSION_MOBILE_ABSOLUTE_DAYS: int = 90

    COOKIE_DOMAIN: str = ""
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "Lax"
    COOKIE_HTTPONLY: bool = True

    ENVIRONMENT: str = "PROD"
    FRONTEND_URL: str = ""
    BANXICO_TOKEN: str = ""

    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    REDIS_URL: str = "redis://localhost:6379/0"
    # Cabecera con la IP real del cliente detrás de un proxy (p. ej. "CF-Connecting-IP").
    # Vacío: se usa la IP de la conexión. Configurarla solo si el origen acepta tráfico
    # únicamente de ese proxy; si no, la cabecera se puede falsificar.
    CLIENT_IP_HEADER: str = ""

    # Correo saliente (verificación de correo y recuperación de contraseña).
    # resend (producción), smtp (Mailpit en local) o memory (tests). Vacío: resend en PROD,
    # smtp en DEV y memory en TEST. En PROD solo se acepta resend con RESEND_API_KEY.
    EMAIL_BACKEND: str = ""
    EMAIL_FROM: str = "Lunance <no-reply@lunance.app>"
    RESEND_API_KEY: SecretStr = SecretStr("")
    # SMTP: por defecto, el puerto SMTP de Mailpit fuera de Docker.
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_STARTTLS: bool = False
    # Base de los enlaces de los correos: la web que abre /verify-email y /reset-password.
    # Vacío: FRONTEND_URL. En PROD debe ser https.
    EMAIL_LINK_BASE_URL: str = ""
    EMAIL_VERIFICATION_TTL_HOURS: int = Field(default=24, gt=0)
    PENDING_SIGNUP_TTL_DAYS: int = Field(default=7, gt=0)
    PASSWORD_RESET_TTL_MINUTES: int = Field(default=60, gt=0)

    AI_PROVIDER: str
    AI_MODEL_ID: str
    AI_API_KEY: str = ""
    AI_BASE_URL: str = ""

    @field_validator("JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY", mode="before")
    @classmethod
    def _unescape_pem(cls, value: Any) -> Any:
        return value.replace("\\n", "\n") if isinstance(value, str) else value

    @model_validator(mode="after")
    def _check_email_settings(self) -> Self:
        environment = self.ENVIRONMENT.upper()
        backend = self.email_backend
        if backend not in EMAIL_BACKENDS:
            raise ValueError(
                f"EMAIL_BACKEND debe ser uno de {', '.join(EMAIL_BACKENDS)}"
            )
        if environment == "PROD":
            if backend != "resend":
                raise ValueError(
                    "En PROD el correo sale por Resend: EMAIL_BACKEND=resend"
                )
            if not self.RESEND_API_KEY.get_secret_value():
                raise ValueError("En PROD hace falta RESEND_API_KEY")
            if not self.email_link_base_url.startswith("https://"):
                raise ValueError(
                    "En PROD, EMAIL_LINK_BASE_URL debe empezar por https://"
                )
        if backend == "resend" and not self.RESEND_API_KEY.get_secret_value():
            raise ValueError("EMAIL_BACKEND=resend necesita RESEND_API_KEY")
        return self

    @property
    def email_backend(self) -> str:
        explicit = self.EMAIL_BACKEND.strip().lower()
        return explicit or DEFAULT_EMAIL_BACKEND.get(self.ENVIRONMENT.upper(), "smtp")

    @property
    def email_link_base_url(self) -> str:
        base = self.EMAIL_LINK_BASE_URL or self.FRONTEND_URL or "http://localhost:3000"
        return base.rstrip("/")

    @property
    def database_url(self) -> str:
        """Async database URL using aiomysql driver"""
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
