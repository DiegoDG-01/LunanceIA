from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Access token: JWT EdDSA (Ed25519). Claves PEM; en .env se aceptan en una línea con "\n".
    # Se generan con `scripts/generate_secrets.py`.
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

    AI_PROVIDER: str
    AI_MODEL_ID: str
    AI_API_KEY: str = ""
    AI_BASE_URL: str = ""

    @field_validator("JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY", mode="before")
    @classmethod
    def _unescape_pem(cls, value: Any) -> Any:
        return value.replace("\\n", "\n") if isinstance(value, str) else value

    @property
    def database_url(self) -> str:
        """Async database URL using aiomysql driver"""
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
