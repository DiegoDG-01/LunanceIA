import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import httpx
from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set environment to TEST before importing app
os.environ["ENVIRONMENT"] = "TEST"

from main import app
from infrastructure.database.connection import Base, get_db
from presentation.dependencies.auth_deps import get_current_user, get_current_active_user
from presentation.dependencies import get_gemini_service
from domain.entities.user import User
from infrastructure.external_services.gemini import GeminiService, GeminiTransactionResult
from domain.objects.enums import TransactionType
from decimal import Decimal
from datetime import date

# Mock Gemini Service
class MockGeminiService:
    async def extract_transaction_data(self, image_data: bytes) -> GeminiTransactionResult:
        return GeminiTransactionResult(
            amount=Decimal("450.00"),
            transaction_type=TransactionType.EXPENSE,
            description="Mocked receipt description",
            notes="Extracted via mock gemini",
            transaction_date=date.today(),
            category_id=1 # Alimentos
        )

def mock_get_gemini_service():
    return MockGeminiService()

# Import models to register them with Base.metadata
import infrastructure.database.models  # noqa: F401

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Mock User for tests
MOCK_USER_ID = 1
MOCK_USER_UUID = "test-user-uuid"
MOCK_AUTH0_ID = "auth0|test-user-id"

async def mock_get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Mock current user for testing, ensuring it exists in the database.
    Checks for Authorization header to support 401 tests.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        from shared.exceptions.base import UnauthorizedError
        raise UnauthorizedError("Missing or invalid token")

    token = auth_header.split(" ")[1]
    if token == "invalid-token":
        from shared.exceptions.base import UnauthorizedError
        raise UnauthorizedError("Invalid token")

    from infrastructure.database.models.user import UserModel
    from sqlalchemy import select

    stmt = select(UserModel).where(UserModel.auth0_id == MOCK_AUTH0_ID)
    result = await db.execute(stmt)
    user_model = result.scalar_one_or_none()
    if not user_model:
        user_model = UserModel(
            id=MOCK_USER_ID,
            uuid=MOCK_USER_UUID,
            auth0_id=MOCK_AUTH0_ID,
            name="Test User",
            email="testuser@gmail.com",
            is_active=True
        )
        db.add(user_model)
        await db.commit()
        await db.refresh(user_model)

    return User(
        id=user_model.id,
        uuid=user_model.uuid,
        auth0_id=user_model.auth0_id,
        name=user_model.name,
        email=user_model.email,
        is_active=user_model.is_active
    )

async def mock_get_current_active_user(current_user: User = Depends(mock_get_current_user)) -> User:
    return current_user

# Use SQLite in-memory for fast tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AsyncTestingSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db(event_loop):
    """Create all tables in the test database and add initial data."""
    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Insert initial data (categories and bank)
        from infrastructure.database.models.category import CategoryModel
        from infrastructure.database.models.bank import BankModel
        from sqlalchemy import select
        async with AsyncTestingSessionLocal() as session:
            stmt = select(CategoryModel)
            result = await session.execute(stmt)
            if not result.scalar_one_or_none():
                categories = [
                    CategoryModel(id=1, name="Alimentos", type="EXPENSE", icon="food", color="#FF0000"),
                    CategoryModel(id=2, name="Salario", type="INCOME", icon="money", color="#00FF00"),
                    CategoryModel(id=3, name="Transporte", type="EXPENSE", icon="car", color="#0000FF"),
                ]
                session.add_all(categories)
                await session.commit()

            stmt = select(BankModel).where(BankModel.id == 1)
            result = await session.execute(stmt)
            if not result.scalar_one_or_none():
                bank = BankModel(id=1, name="Test Bank", code="TST", country="MX", is_active=True)
                session.add(bank)
                await session.commit()

    async def teardown():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        # Close the engine to clean up all connections
        await engine.dispose()

    event_loop.run_until_complete(setup())
    yield
    event_loop.run_until_complete(teardown())


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    async with engine.connect() as connection:
        async with connection.begin() as transaction:
            session = AsyncTestingSessionLocal(bind=connection)

            yield session

            await transaction.rollback()
            await session.close()


@pytest_asyncio.fixture
async def http_client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Integrated HTTP client that talks directly to the FastAPI app with overridden DB.
    Uses the db_session fixture to ensure persistence between requests in the same test.
    """

    async def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_gemini_service] = mock_get_gemini_service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test/api/v2",
        follow_redirects=True
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def test_user_data() -> dict:
    """Test user data."""
    return {
        "name": "Test User",
        "email": "testuser@gmail.com",
        "password": "Password123!"
    }


@pytest.fixture(scope="session")
def debug_user_data() -> dict:
    """Debug user data for testing."""
    return {
        "name": "Debug User",
        "email": "debuguser@gmail.com",
        "password": "Password123!"
    }


@pytest.fixture(scope="session")
def flow_user_data() -> dict:
    """Flow test user data."""
    return {
        "name": "Flow Test User",
        "email": "flowtest@gmail.com",
        "password": "Password123!"
    }


class AuthTokens:
    """Container for authentication tokens."""

    def __init__(self):
        self.access_token: str = "mock-token"
        self.refresh_token: str = "mock-refresh-token"
        self.token_type: str = "Bearer"

    def set_tokens(self, access_token: str, refresh_token: str, token_type: str = "bearer"):
        """Set the authentication tokens."""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type

    def get_auth_headers(self) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"{self.token_type} {self.access_token}"}


@pytest.fixture
def auth_tokens() -> AuthTokens:
    """Authentication tokens container."""
    return AuthTokens()
