from abc import ABC, abstractmethod
from typing import Optional

from pydantic import EmailStr

from domain.entities.user import User


class UserRepository(ABC):
    """Interface for user repository"""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create user"""
        pass

    @abstractmethod
    async def get_by_uuid(self, uuid: str) -> Optional[User]:
        """Get user by uuid"""
        pass

    @abstractmethod
    async def get_by_email(self, email: EmailStr) -> Optional[User]:
        """Get user by email"""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update user"""
        pass

    @abstractmethod
    async def deactivate(self, user: User) -> User:
        """This method is used to softly delete a user"""
        pass

    @abstractmethod
    async def delete(self, user: User) -> User:
        """This method is used to completely delete a user
        this function is only used for users that have been deleted after requesting a deletion"""
        pass

    @abstractmethod
    async def exist_by_email(self, email: EmailStr) -> bool:
        """Check if user exists by email"""
        pass

    @abstractmethod
    async def get_by_username(self, name: str) -> Optional[User]:
        """Get user by username"""
        pass
