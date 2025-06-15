from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


    DB_HOST: str = "localhost"
    DB_PORT: str = "3306"
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
