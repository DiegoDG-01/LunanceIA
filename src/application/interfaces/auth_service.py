from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthConfig:
    access_token_expire_minutes: int
    refresh_token_expire_days: int


class AuthTokenServiceInterface(ABC):
    @abstractmethod
    def check_password(self, plain_password: str, hashed_password: str) -> bool: ...

    @abstractmethod
    def create_access_token(
        self, user_uuid: str, expires_in: int | None = None
    ) -> str: ...

    @abstractmethod
    def create_refresh_token(
        self, user_uuid: str, expires_in: int | None = None
    ) -> str: ...

    @abstractmethod
    async def verify_refresh_token(self, token: str) -> str | None: ...

    @abstractmethod
    def get_password_hash(self, password: str) -> str: ...

    @abstractmethod
    def hash_refresh_token(self, token: str) -> str: ...
