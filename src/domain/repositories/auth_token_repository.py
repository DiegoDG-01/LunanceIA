from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime


class AuthTokenRepository(ABC):
    @abstractmethod
    async def save_refresh_token(
        self, user_id: int, refresh_hash_token: str, expires_at: datetime
    ) -> bool:
        """Save refresh token"""
        pass

    @abstractmethod
    async def get_refresh_token(
        self, user_id: int, refresh_hash_token: str
    ) -> Optional[dict]:
        """Get refresh token"""
        pass

    @abstractmethod
    async def revoke_refresh_token(
        self, user_uuid: str, refresh_hash_token: str
    ) -> bool:
        """Revoke refresh token"""
        pass

    @abstractmethod
    async def revoke_all_refresh_tokens_for_user(self, user_uuid: str) -> bool:
        """Revoke all refresh tokens for user"""
        pass

    @abstractmethod
    async def cleanup_expired_tokens(self) -> bool:
        """Cleanup expired tokens"""
        pass

    @abstractmethod
    async def is_token_valid(self, user_id: int, refresh_hash_token: str) -> bool:
        """Check if token is valid"""
        pass

    @abstractmethod
    async def revoke_token(self, user_uuid: str, refresh_hash_token: str) -> bool:
        """Check if token is revoked"""
        pass

    @abstractmethod
    async def save_token(
        self, user_uuid: str, refresh_hash_token: str, expires_at: datetime
    ) -> bool:
        """Save token"""
        pass
