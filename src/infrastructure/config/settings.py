from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    SECRET_KEY_REFRESH: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ENVIRONMENT: str = "PROD"
    BANXICO_TOKEN: str = ""

    AUTH0_DOMAIN: str
    AUTH0_AUDIENCE: str

    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

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
