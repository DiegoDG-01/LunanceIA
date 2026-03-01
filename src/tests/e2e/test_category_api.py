"""End-to-end tests for category API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens

@pytest.mark.e2e
class TestCategoryAPI:
    """Test category listing and information."""

    @pytest.mark.asyncio
    async def test_get_categories_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test that categories are listed correctly."""
        response = await http_client.get("/category", headers=auth_tokens.get_auth_headers())
        assert response.status_code == 200

        data = response.json()
        assert "categories" in data
        assert "total" in data
        assert data["total"] >= 3 # We created 3 in conftest.py

        # Verify one category structure
        cat = data["categories"][0]
        assert "id" in cat
        assert "name" in cat
        assert "type" in cat
        assert "icon" in cat

    @pytest.mark.asyncio
    async def test_categories_unauthorized(self, http_client: httpx.AsyncClient):
        """Test category access without authentication."""
        response = await http_client.get("/category")
        assert response.status_code == 401
