"""End-to-end tests for investment yield API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens


@pytest.mark.e2e
class TestGetInvestmentYields:
    """Test GET /investments/{account_id}/yields/ endpoint."""

    @pytest.fixture
    async def investment_account(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Create an account for testing investment yields."""
        response = await http_client.post(
            "/account",
            json={
                "name": "Investment Account",
                "account_type": "SAVINGS",
                "bank_id": 1,
                "initial_balance": 10000.0,
                "currency": "MXN",
            },
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code in [200, 201], f"Account creation failed: {response.text}"
        return response.json()

    @pytest.mark.asyncio
    async def test_get_yields_returns_list(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, investment_account):
        """Test that yields endpoint returns a list."""
        account_uuid = investment_account["account_uuid"]

        response = await http_client.get(
            f"/investments/{account_uuid}/yields/",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_yields_not_found(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test yields endpoint with non-existent account."""
        response = await http_client.get(
            "/investments/00000000-0000-0000-0000-000000000000/yields/",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_yields_unauthorized(self, http_client: httpx.AsyncClient):
        """Test yields endpoint without authentication."""
        response = await http_client.get("/investments/some-uuid/yields/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_yields_respects_limit_param(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, investment_account):
        """Test that limit parameter is respected."""
        account_uuid = investment_account["account_uuid"]

        response = await http_client.get(
            f"/investments/{account_uuid}/yields/",
            params={"limit": 10, "offset": 0},
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10


@pytest.mark.e2e
class TestGetInvestmentProjections:
    """Test GET /investments/{account_id}/projections/ endpoint."""

    @pytest.fixture
    async def investment_account(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Create an account for projection testing."""
        response = await http_client.post(
            "/account",
            json={
                "name": "Projection Account",
                "account_type": "SAVINGS",
                "bank_id": 1,
                "initial_balance": 50000.0,
                "currency": "MXN",
            },
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code in [200, 201], f"Account creation failed: {response.text}"
        return response.json()

    @pytest.mark.asyncio
    async def test_get_projections_not_found(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test projections with non-existent account."""
        response = await http_client.get(
            "/investments/00000000-0000-0000-0000-000000000000/projections/",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_projections_unauthorized(self, http_client: httpx.AsyncClient):
        """Test projections without authentication."""
        response = await http_client.get("/investments/some-uuid/projections/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_projections_invalid_days_param(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, investment_account):
        """Test projections with out-of-range days parameter."""
        account_uuid = investment_account["account_uuid"]

        response = await http_client.get(
            f"/investments/{account_uuid}/projections/",
            params={"days": 9999},
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 422
