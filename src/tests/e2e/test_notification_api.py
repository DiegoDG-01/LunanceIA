"""End-to-end tests for notification API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens


@pytest.mark.e2e
class TestGetNotifications:
    """Test GET /notifications endpoint."""

    @pytest.mark.asyncio
    async def test_get_notifications_returns_list(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test that get notifications returns a list (may be empty)."""
        response = await http_client.get(
            "/notifications",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_notifications_unauthorized(self, http_client: httpx.AsyncClient):
        """Test notifications access without authentication."""
        response = await http_client.get("/notifications")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_notifications_invalid_token(self, http_client: httpx.AsyncClient):
        """Test notifications access with invalid token."""
        response = await http_client.get(
            "/notifications",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_notifications_response_structure(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test that notification items have the expected structure."""
        response = await http_client.get(
            "/notifications",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        for notification in data:
            assert "title" in notification
            assert "message" in notification
            assert "type" in notification
            assert "is_read" in notification
