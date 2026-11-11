"""La app con una sesión de BD nueva por petición, como en producción.

El fixture `http_client` de conftest comparte una sola sesión (y una transacción externa)
entre todas las peticiones de un test, así que un rollback dentro de una petición borra lo
que hicieron las anteriores. Los tests de idempotencia necesitan justo eso: reintentos que
se resuelven en otra petición, después de un rollback. Aquí cada petición abre su propia
sesión sobre `engine` y los commits son reales.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from application.idempotency.service import IdempotencyService
from domain.entities.users.user import User
from infrastructure.database.connection import Base, get_db
from infrastructure.database.models.bank import BankModel
from infrastructure.database.models.category import CategoryModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.repositories.sqlalchemy_api_key_repository import (
    SQLAlchemyAPIKeyRepository,
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.security.api_key_service import APIKeyService
from main import app
from presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_user_dual_auth,
)
from presentation.dependencies.idempotency_deps import get_idempotency_service
from presentation.dependencies.repositories import (
    get_idempotency_repository,
    get_unit_of_work_repository,
)
from shared.exceptions.base import UnauthorizedError

USER_IDS = (1, 2)


def bearer(user_id: int = 1) -> dict[str, str]:
    """Header de auth del usuario `user_id` (el token es falso; ver `_user_from_token`)."""
    return {"Authorization": f"Bearer user-{user_id}"}


@dataclass
class IsolatedApp:
    client: httpx.AsyncClient
    sessions: async_sessionmaker[AsyncSession]

    async def count(self, model: Any, *where: Any) -> int:
        async with self.sessions() as session:
            stmt = select(func.count()).select_from(model)
            if where:
                stmt = stmt.where(*where)
            return (await session.execute(stmt)).scalar_one()


async def _user_from_token(request: Request, db: AsyncSession) -> User:
    # Lee el usuario de la BD como la auth real: en MySQL esa lectura fija la foto de
    # REPEATABLE READ antes de reservar la clave, que es el caso que hay que cubrir.
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    user_id = int(token.removeprefix("user-")) if token.startswith("user-") else None
    user = await SQLAlchemyUserRepository(db).get_by_id(user_id) if user_id else None
    if user is None:
        raise UnauthorizedError("Invalid token")
    return user


async def _jwt_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    return await _user_from_token(request, db)


async def _dual_auth_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        service = APIKeyService(
            SQLAlchemyAPIKeyRepository(db),
            SQLAlchemyUserRepository(db),
            SQLAlchemyUnitOfWork(db),
        )
        user, scopes = await service.authenticate(api_key)
        request.state.auth_method = "api_key"
        request.state.api_key_scopes = scopes
        return user
    request.state.auth_method = "jwt"
    return await _user_from_token(request, db)


async def _seed(sessions: async_sessionmaker[AsyncSession]) -> None:
    async with sessions() as session:
        session.add(BankModel(id=1, name="Test Bank", code="TST", country="MX"))
        session.add_all(
            [
                CategoryModel(id=1, name="Alimentos", type="EXPENSE"),
                CategoryModel(id=2, name="Salario", type="INCOME"),
            ]
        )
        session.add_all(
            [
                UserModel(
                    id=user_id,
                    uuid=f"user-{user_id}",
                    name=f"Usuario {user_id}",
                    email=f"usuario{user_id}@example.com",
                )
                for user_id in USER_IDS
            ]
        )
        await session.commit()


@asynccontextmanager
async def isolated_app(
    engine: AsyncEngine, *, wait_timeout: float = 0.2
) -> AsyncIterator[IsolatedApp]:
    """Crea el esquema en `engine`, siembra datos mínimos y sobreescribe `get_db`.

    `wait_timeout` es lo que un reintento espera a la respuesta de la petición
    original antes de responder 409 (corto para que el test del 409 no tarde).
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    await _seed(sessions)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    def override_idempotency_service(
        repository=Depends(get_idempotency_repository),
        uow=Depends(get_unit_of_work_repository),
    ) -> IdempotencyService:
        return IdempotencyService(repository, uow, wait_timeout=wait_timeout)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = _jwt_user
    app.dependency_overrides[get_user_dual_auth] = _dual_auth_user
    app.dependency_overrides[get_idempotency_service] = override_idempotency_service
    try:
        # raise_app_exceptions=False: un 500 se devuelve como respuesta en lugar de
        # propagar la excepción al test (lo necesita el test del proceso que "muere").
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test/api/v2",
            follow_redirects=True,
        ) as client:
            yield IsolatedApp(client=client, sessions=sessions)
    finally:
        app.dependency_overrides.clear()
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
