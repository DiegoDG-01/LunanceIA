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
            "bank_id": 1,
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


@pytest.mark.e2e
class TestGetSubscriptionById:
    """Test GET /subscription/{subscription_uuid}/ endpoint."""

    @pytest.fixture
    async def created_subscription(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        acc_res = await http_client.post(
            "/account",
            json={"name": "GetSub Account", "account_type": "CHECKING", "bank_id": 1, "initial_balance": 5000.0, "currency": "MXN"},
            headers=auth_tokens.get_auth_headers(),
        )
        account_uuid = acc_res.json()["account_uuid"]
        sub_res = await http_client.post(
            "/subscription",
            json={"account_uuid": account_uuid, "category_id": 1, "name": "Spotify", "amount": 99.0, "frequency": "MONTHLY", "start_date": str(date.today()), "billing_day": 5},
            headers=auth_tokens.get_auth_headers(),
        )
        return sub_res.json()

    @pytest.mark.asyncio
    async def test_get_subscription_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_subscription):
        sub_uuid = created_subscription["uuid"]

        response = await http_client.get(f"/subscription/{sub_uuid}/", headers=auth_tokens.get_auth_headers())

        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == sub_uuid
        assert data["name"] == "Spotify"

    @pytest.mark.asyncio
    async def test_get_subscription_not_found(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await http_client.get(
            "/subscription/00000000-0000-0000-0000-000000000000/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_subscription_unauthorized(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/subscription/some-uuid/")
        assert response.status_code == 401


@pytest.mark.e2e
class TestUpdateSubscription:
    """Test PUT /subscription/{subscription_uuid}/ endpoint."""

    @pytest.fixture
    async def created_subscription(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        acc_res = await http_client.post(
            "/account",
            json={"name": "UpdateSub Account", "account_type": "CHECKING", "bank_id": 1, "initial_balance": 5000.0, "currency": "MXN"},
            headers=auth_tokens.get_auth_headers(),
        )
        account_uuid = acc_res.json()["account_uuid"]
        sub_res = await http_client.post(
            "/subscription",
            json={"account_uuid": account_uuid, "category_id": 1, "name": "HBO", "amount": 149.0, "frequency": "MONTHLY", "start_date": str(date.today()), "billing_day": 10},
            headers=auth_tokens.get_auth_headers(),
        )
        return {"account_uuid": account_uuid, "subscription": sub_res.json()}

    @pytest.mark.asyncio
    async def test_update_subscription_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_subscription):
        sub_uuid = created_subscription["subscription"]["uuid"]
        account_uuid = created_subscription["account_uuid"]

        response = await http_client.put(
            f"/subscription/{sub_uuid}/",
            json={"account_uuid": account_uuid, "name": "HBO Max", "amount": 199.0, "frequency": "MONTHLY", "start_date": str(date.today()), "billing_day": 10, "is_active": True},
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        assert response.json()["name"] == "HBO Max"
        assert float(response.json()["amount"]) == 199.0

    @pytest.mark.asyncio
    async def test_update_subscription_not_found(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await http_client.put(
            "/subscription/00000000-0000-0000-0000-000000000000/",
            json={"name": "Updated", "amount": 99.0, "frequency": "MONTHLY", "start_date": str(date.today()), "billing_day": 1, "is_active": True},
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code in [404, 422]

    @pytest.mark.asyncio
    async def test_update_subscription_unauthorized(self, http_client: httpx.AsyncClient):
        response = await http_client.put(
            "/subscription/some-uuid/",
            json={"name": "x", "amount": 10.0, "frequency": "MONTHLY", "start_date": str(date.today()), "billing_day": 1},
        )
        assert response.status_code == 401


@pytest.mark.e2e
class TestActivateSubscription:
    """Test PATCH /subscription/{subscription_uuid}/activate/ endpoint."""

    @pytest.fixture
    async def created_subscription(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        acc_res = await http_client.post(
            "/account",
            json={"name": "ActivateSub Account", "account_type": "CHECKING", "bank_id": 1, "initial_balance": 5000.0, "currency": "MXN"},
            headers=auth_tokens.get_auth_headers(),
        )
        account_uuid = acc_res.json()["account_uuid"]
        sub_res = await http_client.post(
            "/subscription",
            json={"account_uuid": account_uuid, "category_id": 1, "name": "Disney+", "amount": 129.0, "frequency": "MONTHLY", "start_date": str(date.today()), "billing_day": 15},
            headers=auth_tokens.get_auth_headers(),
        )
        return sub_res.json()

    @pytest.mark.asyncio
    async def test_toggle_subscription_status(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_subscription):
        sub_uuid = created_subscription["uuid"]
        original_status = created_subscription["is_active"]

        response = await http_client.patch(
            f"/subscription/{sub_uuid}/activate/",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        assert response.json()["is_active"] != original_status

    @pytest.mark.asyncio
    async def test_toggle_subscription_not_found(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await http_client.patch(
            "/subscription/00000000-0000-0000-0000-000000000000/activate/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_toggle_subscription_unauthorized(self, http_client: httpx.AsyncClient):
        response = await http_client.patch("/subscription/some-uuid/activate/")
        assert response.status_code == 401


@pytest.mark.e2e
class TestDeleteSubscription:
    """Test DELETE /subscription/{subscription_uuid}/ endpoint."""

    @pytest.fixture
    async def created_subscription(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        acc_res = await http_client.post(
            "/account",
            json={"name": "DeleteSub Account", "account_type": "CHECKING", "bank_id": 1, "initial_balance": 5000.0, "currency": "MXN"},
            headers=auth_tokens.get_auth_headers(),
        )
        account_uuid = acc_res.json()["account_uuid"]
        sub_res = await http_client.post(
            "/subscription",
            json={"account_uuid": account_uuid, "category_id": 1, "name": "Apple TV", "amount": 89.0, "frequency": "MONTHLY", "start_date": str(date.today()), "billing_day": 20},
            headers=auth_tokens.get_auth_headers(),
        )
        return sub_res.json()

    @pytest.mark.asyncio
    async def test_delete_subscription_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_subscription):
        sub_uuid = created_subscription["uuid"]

        response = await http_client.delete(
            f"/subscription/{sub_uuid}/",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_subscription_not_found(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await http_client.delete(
            "/subscription/00000000-0000-0000-0000-000000000000/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_subscription_unauthorized(self, http_client: httpx.AsyncClient):
        response = await http_client.delete("/subscription/some-uuid/")
        assert response.status_code == 401


@pytest.mark.e2e
class TestGetSubscriptionCharges:
    """Test GET /subscription/charges/ endpoint."""

    @pytest.mark.asyncio
    async def test_get_charges_returns_list(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await http_client.get(
            "/subscription/charges/",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_charges_unauthorized(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/subscription/charges/")
        assert response.status_code == 401


@pytest.mark.e2e
class TestGetSubscriptionTransactions:
    """Test GET /subscription/{subscription_uuid}/transactions/ endpoint."""

    @pytest.fixture
    async def created_subscription(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        acc_res = await http_client.post(
            "/account",
            json={"name": "SubTx Account", "account_type": "CHECKING", "bank_id": 1, "initial_balance": 5000.0, "currency": "MXN"},
            headers=auth_tokens.get_auth_headers(),
        )
        account_uuid = acc_res.json()["account_uuid"]
        sub_res = await http_client.post(
            "/subscription",
            json={"account_uuid": account_uuid, "category_id": 1, "name": "Paramount+", "amount": 79.0, "frequency": "MONTHLY", "start_date": str(date.today()), "billing_day": 25},
            headers=auth_tokens.get_auth_headers(),
        )
        return sub_res.json()

    @pytest.mark.asyncio
    async def test_get_subscription_transactions_empty(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_subscription):
        sub_uuid = created_subscription["uuid"]

        response = await http_client.get(
            f"/subscription/{sub_uuid}/transactions/",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_subscription_transactions_not_found(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await http_client.get(
            "/subscription/00000000-0000-0000-0000-000000000000/transactions/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_subscription_transactions_unauthorized(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/subscription/some-uuid/transactions/")
        assert response.status_code == 401
