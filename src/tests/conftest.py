"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
import httpx


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for API tests."""
    return "http://127.0.0.1:8000/api/v2"


@pytest_asyncio.fixture
async def http_client(base_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """HTTP client for API tests.""" 
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def test_user_data() -> dict:
    """Test user data with strong password."""
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
        self.access_token: str = ""
        self.refresh_token: str = ""
        self.token_type: str = "bearer"
    
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