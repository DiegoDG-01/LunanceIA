"""Fixtures para los handlers de sesión: repositorios reales sobre SQLite, Redis falso y reloj
controlable. Las claves y los parámetros de Argon2 son de prueba (rápidos)."""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from application.auth.commands.login import LoginCommand, LoginHandler
from application.auth.commands.logout import LogoutHandler
from application.auth.commands.purge_auth_data import PurgeAuthDataHandler
from application.auth.commands.refresh_session import RefreshSessionHandler
from application.auth.commands.revoke_session import RevokeSessionHandler
from application.auth.config import AuthConfig
from application.auth.dto import ClientContext
from application.auth.queries.list_sessions import ListSessionsHandler
from application.auth.services.sessions import SessionManager
from domain.entities.auth.session import Platform, SessionLifetime
from infrastructure.cache.session_revocations import PersistentSessionRevocations
from infrastructure.database.connection import Base
from infrastructure.database.models.user import UserModel
from infrastructure.database.repositories.sqlalchemy_auth_event_repository import (
    SQLAlchemyAuthEventRepository,
)
from infrastructure.database.repositories.sqlalchemy_refresh_token_repository import (
    SQLAlchemyRefreshTokenRepository,
)
from infrastructure.database.repositories.sqlalchemy_session_repository import (
    SQLAlchemySessionRepository,
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.security.jwt_tokens import EdDSATokenIssuer
from infrastructure.security.passwords import Argon2PasswordHasher
from tests.auth_helpers import BrokenRedis, fast_hasher, make_issuer  # noqa: F401

PASSWORD = "Password123!"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


def context(
    device_id: str | None = None,
    platform: Platform = Platform.WEB,
    ip: str = "203.0.113.5",
) -> ClientContext:
    return ClientContext(
        device_id=device_id or str(uuid.uuid4()),
        platform=platform,
        client=f"{platform.value}/1.0.0",
        ip=ip,
        user_agent="pytest",
    )


@dataclass
class AuthKit:
    """Todo lo necesario para ejercitar los handlers contra la base de test."""

    db: object
    clock: Clock
    redis: object
    config: AuthConfig
    issuer: EdDSATokenIssuer
    hasher: Argon2PasswordHasher
    users: SQLAlchemyUserRepository
    sessions: SQLAlchemySessionRepository
    tokens: SQLAlchemyRefreshTokenRepository
    events: SQLAlchemyAuthEventRepository
    uow: SQLAlchemyUnitOfWork
    revocations: PersistentSessionRevocations

    def manager(self) -> SessionManager:
        return SessionManager(
            session_repository=self.sessions,
            refresh_token_repository=self.tokens,
            auth_event_repository=self.events,
            token_issuer=self.issuer,
            config=self.config,
        )

    def login_handler(self) -> LoginHandler:
        return LoginHandler(
            user_repository=self.users,
            auth_event_repository=self.events,
            session_manager=self.manager(),
            password_hasher=self.hasher,
            revocations=self.revocations,
            uow=self.uow,
            now=self.clock,
        )

    def refresh_handler(self) -> RefreshSessionHandler:
        return RefreshSessionHandler(
            user_repository=self.users,
            session_repository=self.sessions,
            refresh_token_repository=self.tokens,
            auth_event_repository=self.events,
            session_manager=self.manager(),
            revocations=self.revocations,
            uow=self.uow,
            config=self.config,
            now=self.clock,
        )

    def logout_handler(self) -> LogoutHandler:
        return LogoutHandler(
            session_repository=self.sessions,
            refresh_token_repository=self.tokens,
            auth_event_repository=self.events,
            revocations=self.revocations,
            uow=self.uow,
            now=self.clock,
        )

    def revoke_handler(self) -> RevokeSessionHandler:
        return RevokeSessionHandler(
            session_repository=self.sessions,
            auth_event_repository=self.events,
            revocations=self.revocations,
            uow=self.uow,
            now=self.clock,
        )

    def list_handler(self) -> ListSessionsHandler:
        return ListSessionsHandler(session_repository=self.sessions, now=self.clock)

    def purge_handler(self) -> PurgeAuthDataHandler:
        return PurgeAuthDataHandler(
            session_repository=self.sessions,
            auth_event_repository=self.events,
            uow=self.uow,
            now=self.clock,
        )

    async def create_user(
        self, name: str | None = None, password_hash: str | None = None, **fields
    ) -> UserModel:
        model = UserModel(
            name=name or f"user_{uuid.uuid4().hex[:10]}",
            password=password_hash or await self.hasher.hash(PASSWORD),
            **fields,
        )
        self.db.add(model)  # type: ignore[attr-defined]
        await self.db.flush()  # type: ignore[attr-defined]
        return model

    async def login(self, user: UserModel, ctx: ClientContext):
        return await self.login_handler().handle(
            LoginCommand(username=user.name, password=PASSWORD, context=ctx)
        )


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest_asyncio.fixture
async def auth_db():
    """Base propia y vacía por test, con commit y rollback reales (como una petición)."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False, autoflush=False)() as db:
        yield db
    await engine.dispose()


@pytest_asyncio.fixture
async def kit(auth_db, clock) -> AuthKit:
    db_session = auth_db
    redis = FakeAsyncRedis(decode_responses=True)
    sessions = SQLAlchemySessionRepository(db_session)
    issuer = make_issuer()
    return AuthKit(
        db=db_session,
        clock=clock,
        redis=redis,
        config=AuthConfig(
            web_session=SessionLifetime(timedelta(days=1), timedelta(days=7)),
            mobile_session=SessionLifetime(timedelta(days=30), timedelta(days=90)),
            refresh_reuse_grace=timedelta(seconds=30),
            refresh_rotation_key=secrets.token_bytes(32),
        ),
        issuer=issuer,
        hasher=fast_hasher(),
        users=SQLAlchemyUserRepository(db_session),
        sessions=sessions,
        tokens=SQLAlchemyRefreshTokenRepository(db_session),
        events=SQLAlchemyAuthEventRepository(db_session),
        uow=SQLAlchemyUnitOfWork(db_session),
        revocations=PersistentSessionRevocations(
            lambda: redis,
            ttl_seconds=issuer.ttl_seconds,
            session_repository=sessions,
            now=clock,
        ),
    )
