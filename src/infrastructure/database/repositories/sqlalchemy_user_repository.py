from typing import Optional
from sqlalchemy import exists
from sqlalchemy.orm import Session

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.database.models.user import UserModel


class SQLAlchemyUserRepository(UserRepository):
    """Implementación SQLAlchemy del repositorio de usuarios."""

    def __init__(self, db: Session):
        self.db = db

    def _model_to_entity(self, model: UserModel) -> User:
        """Convierte modelo SQLAlchemy a entidad de dominio."""
        return User(
            id=model.id,
            uuid=model.uuid,
            name=model.name,
            email=model.email,
            password_hash=model.password_hash,
            registration_date=model.registration_date,
            is_active=model.is_active,
        )

    def _entity_to_model(self, entity: User) -> UserModel:
        """Convierte entidad de dominio a modelo SQLAlchemy."""
        return UserModel(
            id=entity.id,
            uuid=entity.uuid,
            name=entity.name,
            email=entity.email,
            password_hash=entity.password_hash,
            registration_date=entity.registration_date,
            is_active=entity.is_active,
        )

    def create(self, user: User) -> User:
        """Crea un nuevo usuario."""
        model = self._entity_to_model(user)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Obtiene usuario por ID."""
        model = self.db.query(UserModel).filter(UserModel.id == user_id).first()

        return self._model_to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Obtiene usuario por email."""
        model = self.db.query(UserModel).filter(UserModel.email == email).first()

        return self._model_to_entity(model) if model else None

    async def get_by_uuid(self, uuid: str) -> Optional[User]:
        """Obtiene usuario por UUID."""
        model = self.db.query(UserModel).filter(UserModel.uuid == uuid).first()

        return self._model_to_entity(model) if model else None

    async def update(self, user: User) -> User:
        """Actualiza un usuario."""
        model = self.db.query(UserModel).filter(UserModel.id == user.id).first()

        if not model:
            raise ValueError("Usuario no encontrado")

        # Actualizar campos
        model.name = user.name
        model.email = user.email
        model.password_hash = user.password_hash
        model.is_active = user.is_active

        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    async def deactivate(self, user: User) -> User:
        """Desactiva un usuario (soft delete)."""
        model = self.db.query(UserModel).filter(UserModel.id == user.id).first()

        if not model:
            raise ValueError("Usuario no encontrado")

        model.is_active = False
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, user: User) -> User:
        """Elimina completamente un usuario."""
        model = self.db.query(UserModel).filter(UserModel.id == user.id).first()

        if not model:
            raise ValueError("Usuario no encontrado")

        self.db.delete(model)
        self.db.commit()
        return user

    async def exist_by_email(self, email: str) -> bool:
        """Verifica si existe un usuario con el email dado."""
        return self.db.query(
            exists().where(UserModel.email == email)
        ).scalar()

    async def exists_by_email(self, email: str) -> bool:
        """Verifica si existe un usuario con el email dado (alias)."""
        return await self.exist_by_email(email)
