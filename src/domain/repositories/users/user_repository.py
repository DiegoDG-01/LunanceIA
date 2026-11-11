from abc import ABC, abstractmethod

from pydantic import EmailStr

from domain.entities.users.user import User


class UserRepository(ABC):
    """Interface for user repository"""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create user"""

    @abstractmethod
    async def get_by_uuid(self, uuid: str) -> User | None:
        """Get user by uuid"""

    @abstractmethod
    async def get_by_email(self, email: EmailStr) -> User | None:
        """Usuario por correo, ya normalizado (`shared.utils.emails.normalize_email`)."""

    @abstractmethod
    async def get_by_id(self, user_id: int, *, for_update: bool = False) -> User | None:
        """Get user by ID. `for_update` bloquea la fila hasta el fin de la transacción."""

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update user"""

    @abstractmethod
    async def deactivate(self, user: User) -> User:
        """This method is used to softly delete a user"""

    @abstractmethod
    async def delete(self, user: User) -> User:
        """This method is used to completely delete a user
        this function is only used for users that have been deleted after requesting a deletion"""

    @abstractmethod
    async def exist_by_email(self, email: EmailStr) -> bool:
        """Check if user exists by email"""

    @abstractmethod
    async def get_by_username(self, name: str) -> User | None:
        """Get user by username"""
