from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    SECRET_KEY_REFRESH: str
    ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    GEMINI_API_KEY: str
    GEMINI_MODEL_ID: str

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
