import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
import httpx
from fastapi import Depends, Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set environment to TEST before importing app
os.environ["ENVIRONMENT"] = "TEST"

from main import app
from infrastructure.database.connection import Base, get_db
from presentation.dependencies.auth_deps import get_current_user, get_current_active_user
from presentation.dependencies.service_deps import get_gemini_service
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

# Mock User for tests
MOCK_USER_ID = 1
MOCK_USER_UUID = "test-user-uuid"
MOCK_AUTH0_ID = "auth0|test-user-id"

async def mock_get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
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

    user_model = db.query(UserModel).filter(UserModel.auth0_id == MOCK_AUTH0_ID).first()
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
        db.commit()
        db.refresh(user_model)

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
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in the test database and add initial data."""
    Base.metadata.create_all(bind=engine)

    # Insert initial data (categories)
    from infrastructure.database.models.category import CategoryModel
    with TestingSessionLocal() as session:
        if not session.query(CategoryModel).first():
            categories = [
                CategoryModel(id=1, name="Alimentos", type="EXPENSE", icon="food", color="#FF0000"),
                CategoryModel(id=2, name="Salario", type="INCOME", icon="money", color="#00FF00"),
                CategoryModel(id=3, name="Transporte", type="EXPENSE", icon="car", color="#0000FF"),
            ]
            session.add_all(categories)
            session.commit()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a clean database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest_asyncio.fixture
async def http_client(db_session: Session) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Integrated HTTP client that talks directly to the FastAPI app with overridden DB.
    Uses the db_session fixture to ensure persistence between requests in the same test.
    """

    def override_get_db():
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
