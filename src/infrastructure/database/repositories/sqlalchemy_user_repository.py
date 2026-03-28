from typing import Optional
from datetime import datetime
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.database.models.user import UserModel


class SQLAlchemyUserRepository(UserRepository):
    """Implementación SQLAlchemy del repositorio de usuarios."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _model_to_entity(self, model: UserModel) -> User:
        """Convierte modelo SQLAlchemy a entidad de dominio."""
        return User(
            id=model.id,
            uuid=model.uuid,
            auth0_id=model.auth0_id,
            name=model.name,
            email=model.email,
            password=model.password,
            picture=model.picture,
            email_verified=model.email_verified,
            last_login=model.last_login or datetime.now(),
            registration_date=model.registration_date,
            is_active=model.is_active,
        )

    def _entity_to_model(self, entity: User) -> UserModel:
        """Convierte entidad de dominio a modelo SQLAlchemy."""
        return UserModel(
            id=entity.id,
            uuid=entity.uuid,
            auth0_id=entity.auth0_id,
            name=entity.name,
            email=entity.email,
            password=entity.password,
            picture=entity.picture,
            email_verified=entity.email_verified,
            last_login=entity.last_login,
            registration_date=entity.registration_date,
            is_active=entity.is_active,
        )

    async def create(self, user: User) -> User:
        """Crea un nuevo usuario."""
        model = self._entity_to_model(user)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Obtiene usuario por ID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_auth0_uuid(self, id: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.auth0_id == id)
        result = await self.db.execute(stmt)
        user_model = result.scalar_one_or_none()
        return self._model_to_entity(user_model) if user_model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Obtiene usuario por email."""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_uuid(self, uuid: str) -> Optional[User]:
        """Obtiene usuario por UUID."""
        stmt = select(UserModel).where(UserModel.uuid == uuid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def update(self, user: User) -> User:
        """Actualiza un usuario."""
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError("Usuario no encontrado")

        # Actualizar campos
        model.name = user.name
        model.password = user.password
        model.is_active = user.is_active

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def deactivate(self, user: User) -> User:
        """Desactiva un usuario (soft delete)."""
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError("Usuario no encontrado")

        model.is_active = False
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, user: User) -> User:
        """Elimina completamente un usuario."""
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError("Usuario no encontrado")

        await self.db.delete(model)
        await self.db.flush()
        return user

    async def exist_by_email(self, email: str) -> bool:
        """Verifica si existe un usuario con el email dado."""
        stmt = select(exists().where(UserModel.email == email))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def exists_by_email(self, email: str) -> bool:
        """Verifica si existe un usuario con el email dado (alias)."""
        return await self.exist_by_email(email)

    async def get_by_username(self, name: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.name == name)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None
