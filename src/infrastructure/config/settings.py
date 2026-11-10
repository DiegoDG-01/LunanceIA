from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    SECRET_KEY_REFRESH: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

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

    @property
    def database_url(self) -> str:
        """Async database URL using aiomysql driver"""
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
