"""End-to-end tests for subscription API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens
from datetime import date

@pytest.mark.e2e
class TestSubscriptionCRUD:
    """Test subscription management and charge generation."""

    @pytest.fixture
    async def test_account(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Helper fixture to create a test account."""
        account_data = {
            "name": "Subscription Test Account",
            "account_type": "CHECKING",
            "bank": "Test Bank",
            "initial_balance": 5000.00,
            "currency": "MXN"
        }
        response = await http_client.post("/account", json=account_data, headers=auth_tokens.get_auth_headers())
        return response.json()

    @pytest.mark.asyncio
    async def test_create_subscription_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, test_account):
        """Test successful creation of a subscription."""
        account_uuid = test_account["account_uuid"]

        subscription_data = {
            "account_uuid": account_uuid,
            "category_id": 1,
            "name": "Netflix",
            "amount": 199.00,
            "frequency": "MONTHLY",
            "start_date": str(date.today()),
            "billing_day": 1,
            "description": "Streaming service"
        }

        response = await http_client.post(
            "/subscription",
            json=subscription_data,
            headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Netflix"
        assert float(data["amount"]) == 199.00
        assert data["is_active"] is True
        assert "uuid" in data

    @pytest.mark.asyncio
    async def test_get_subscriptions_list(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, test_account):
        """Test listing user subscriptions."""
        response = await http_client.get("/subscription", headers=auth_tokens.get_auth_headers())
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_subscription_unauthorized(self, http_client: httpx.AsyncClient):
        """Test subscription access without authentication."""
        response = await http_client.get("/subscription")
        assert response.status_code == 401
