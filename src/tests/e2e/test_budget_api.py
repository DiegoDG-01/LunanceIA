"""End-to-end tests for budget API endpoints."""

from datetime import date

import pytest
import httpx

from ..conftest import AuthTokens


@pytest.mark.e2e
class TestBudgetCRUD:
    """Test /budgets/ CRUD endpoints."""

    async def _create_budget(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, **overrides
    ) -> httpx.Response:
        payload = {
            "name": "Comida mensual",
            "limit_amount": 5000.00,
            "period": "mensual",
            "start_date": str(date.today()),
            "category_id": 1,
            "alert_percentage": 80,
        }
        payload.update(overrides)
        return await http_client.post(
            "/budgets/", json=payload, headers=auth_tokens.get_auth_headers()
        )

    @pytest.mark.asyncio
    async def test_create_budget_success(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await self._create_budget(http_client, auth_tokens)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Comida mensual"
        assert float(data["limit_amount"]) == 5000.00
        assert data["period"] == "mensual"
        assert data["is_active"] is True
        assert data["alert_percentage"] == 80
        assert "uuid" in data

    @pytest.mark.asyncio
    async def test_create_budget_invalid_amount(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await self._create_budget(http_client, auth_tokens, limit_amount=-100)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_budgets_list(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        await self._create_budget(http_client, auth_tokens, name="Budget en lista")

        response = await http_client.get("/budgets/", headers=auth_tokens.get_auth_headers())

        assert response.status_code == 200
        names = [b["name"] for b in response.json()]
        assert "Budget en lista" in names

    @pytest.mark.asyncio
    async def test_get_budget_by_uuid(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        created = (await self._create_budget(http_client, auth_tokens)).json()

        response = await http_client.get(
            f"/budgets/{created['uuid']}/", headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200
        assert response.json()["uuid"] == created["uuid"]

    @pytest.mark.asyncio
    async def test_get_budget_not_found(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await http_client.get(
            "/budgets/00000000-0000-0000-0000-000000000000/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_budget_progress(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        created = (await self._create_budget(http_client, auth_tokens)).json()

        response = await http_client.get(
            f"/budgets/{created['uuid']}/progress/", headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["limit_amount"]) == 5000.00
        assert float(data["spent_amount"]) == 0.0
        assert data["is_limit_exceeded"] is False
        assert data["is_alert_triggered"] is False

    @pytest.mark.asyncio
    async def test_update_budget(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        created = (await self._create_budget(http_client, auth_tokens)).json()

        response = await http_client.patch(
            f"/budgets/{created['uuid']}/",
            json={"limit_amount": 6000.00, "alert_percentage": 75},
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["limit_amount"]) == 6000.00
        assert data["alert_percentage"] == 75

    @pytest.mark.asyncio
    async def test_toggle_budget_status(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        created = (await self._create_budget(http_client, auth_tokens)).json()
        assert created["is_active"] is True

        response = await http_client.patch(
            f"/budgets/{created['uuid']}/activate/", headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_budget(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        created = (await self._create_budget(http_client, auth_tokens)).json()

        response = await http_client.delete(
            f"/budgets/{created['uuid']}/", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 204

        response = await http_client.get(
            f"/budgets/{created['uuid']}/", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_budgets_unauthorized(self, http_client: httpx.AsyncClient):
        response = await http_client.get("/budgets/")
        assert response.status_code == 401
