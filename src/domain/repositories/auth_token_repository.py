from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from domain.entities.refresh_token import RefreshToken


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
    ) -> Optional[RefreshToken]:
        """Get refresh token"""
        pass

    @abstractmethod
    async def revoke_refresh_token(
        self, user_id: int, refresh_hash_token: str
    ) -> bool:
        """Revoke refresh token"""
        pass

    @abstractmethod
    async def revoke_all_refresh_tokens_for_user(self, user_id: int) -> bool:
        """Revoke all refresh tokens for user"""
        pass

    @abstractmethod
    async def cleanup_expired_tokens(self) -> bool:
        """Cleanup expired tokens"""
        pass
