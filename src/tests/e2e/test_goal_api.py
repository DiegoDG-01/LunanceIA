"""End-to-end tests for saving goals API endpoints."""

from datetime import date, timedelta

import pytest
import httpx

from ..conftest import AuthTokens


@pytest.mark.e2e
class TestSavingGoalCRUD:
    """Test /goals/ CRUD endpoints."""

    @pytest.fixture
    async def test_account(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await http_client.post(
            "/account",
            json={
                "name": "Goal Test Account",
                "account_type": "SAVINGS",
                "bank_id": 1,
                "initial_balance": 1000.00,
                "currency": "MXN",
            },
            headers=auth_tokens.get_auth_headers(),
        )
        return response.json()

    async def _create_goal(
        self,
        http_client: httpx.AsyncClient,
        auth_tokens: AuthTokens,
        account_uuid: str,
        **overrides,
    ) -> httpx.Response:
        payload = {
            "account_uuid": account_uuid,
            "name": "Vacaciones",
            "target_amount": 20000.00,
            "target_date": str(date.today() + timedelta(days=365)),
            "description": "Ahorro para vacaciones",
        }
        payload.update(overrides)
        return await http_client.post(
            "/goals/", json=payload, headers=auth_tokens.get_auth_headers()
        )

    @pytest.mark.asyncio
    async def test_create_goal_success(self, http_client, auth_tokens, test_account):
        response = await self._create_goal(
            http_client, auth_tokens, test_account["account_uuid"]
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Vacaciones"
        assert float(data["target_amount"]) == 20000.00
        assert data["account_uuid"] == test_account["account_uuid"]
        assert data["is_active"] is True
        assert "uuid" in data

    @pytest.mark.asyncio
    async def test_create_goal_invalid_amount(self, http_client, auth_tokens, test_account):
        response = await self._create_goal(
            http_client, auth_tokens, test_account["account_uuid"], target_amount=-1
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_goals_list(self, http_client, auth_tokens, test_account):
        await self._create_goal(
            http_client, auth_tokens, test_account["account_uuid"], name="Meta en lista"
        )

        response = await http_client.get("/goals/", headers=auth_tokens.get_auth_headers())

        assert response.status_code == 200
        names = [g["name"] for g in response.json()]
        assert "Meta en lista" in names

    @pytest.mark.asyncio
    async def test_get_goal_by_uuid(self, http_client, auth_tokens, test_account):
        created = (
            await self._create_goal(http_client, auth_tokens, test_account["account_uuid"])
        ).json()

        response = await http_client.get(
            f"/goals/{created['uuid']}/", headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200
        assert response.json()["uuid"] == created["uuid"]

    @pytest.mark.asyncio
    async def test_get_goal_not_found(self, http_client, auth_tokens):
        response = await http_client.get(
            "/goals/00000000-0000-0000-0000-000000000000/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_goal(self, http_client, auth_tokens, test_account):
        created = (
            await self._create_goal(http_client, auth_tokens, test_account["account_uuid"])
        ).json()

        response = await http_client.put(
            f"/goals/{created['uuid']}/",
            json={"name": "Vacaciones Europa", "target_amount": 30000.00},
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Vacaciones Europa"
        assert float(data["target_amount"]) == 30000.00

    @pytest.mark.asyncio
    async def test_toggle_goal_status(self, http_client, auth_tokens, test_account):
        created = (
            await self._create_goal(http_client, auth_tokens, test_account["account_uuid"])
        ).json()
        assert created["is_active"] is True

        response = await http_client.patch(
            f"/goals/{created['uuid']}/activate/", headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_goal(self, http_client, auth_tokens, test_account):
        created = (
            await self._create_goal(http_client, auth_tokens, test_account["account_uuid"])
        ).json()

        response = await http_client.delete(
            f"/goals/{created['uuid']}/", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 204

        response = await http_client.get(
            f"/goals/{created['uuid']}/", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_goals_unauthorized(self, http_client):
        response = await http_client.get("/goals/")
        assert response.status_code == 401
