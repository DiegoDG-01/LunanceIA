"""End-to-end tests for transfer API endpoints."""

from datetime import date

import pytest
import httpx

from ..conftest import AuthTokens


@pytest.mark.e2e
class TestTransferCRUD:
    """Test /transfers/ endpoints and impact on account balances."""

    async def _create_account(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, name: str, balance: float
    ) -> dict:
        response = await http_client.post(
            "/account",
            json={
                "name": name,
                "account_type": "CHECKING",
                "bank_id": 1,
                "initial_balance": balance,
                "currency": "MXN",
            },
            headers=auth_tokens.get_auth_headers(),
        )
        return response.json()

    async def _get_balance(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, account_uuid: str
    ) -> float:
        response = await http_client.get(
            f"/account/{account_uuid}", headers=auth_tokens.get_auth_headers()
        )
        return float(response.json()["current_balance"])

    @pytest.mark.asyncio
    async def test_create_transfer_moves_balance(self, http_client, auth_tokens):
        source = await self._create_account(http_client, auth_tokens, "Transfer Source", 1000.00)
        destination = await self._create_account(http_client, auth_tokens, "Transfer Dest", 500.00)

        response = await http_client.post(
            "/transfers/",
            json={
                "source_account_uuid": source["account_uuid"],
                "destination_account_uuid": destination["account_uuid"],
                "amount": 300.00,
                "description": "Pago tarjeta",
                "transfer_date": str(date.today()),
            },
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 201
        data = response.json()
        assert float(data["amount"]) == 300.00
        assert data["source_account_uuid"] == source["account_uuid"]
        assert data["destination_account_uuid"] == destination["account_uuid"]
        assert "transfer_uuid" in data

        assert await self._get_balance(http_client, auth_tokens, source["account_uuid"]) == 700.00
        assert await self._get_balance(http_client, auth_tokens, destination["account_uuid"]) == 800.00

    @pytest.mark.asyncio
    async def test_delete_transfer_reverts_balances(self, http_client, auth_tokens):
        source = await self._create_account(http_client, auth_tokens, "Revert Source", 1000.00)
        destination = await self._create_account(http_client, auth_tokens, "Revert Dest", 500.00)

        created = (
            await http_client.post(
                "/transfers/",
                json={
                    "source_account_uuid": source["account_uuid"],
                    "destination_account_uuid": destination["account_uuid"],
                    "amount": 200.00,
                    "transfer_date": str(date.today()),
                },
                headers=auth_tokens.get_auth_headers(),
            )
        ).json()

        response = await http_client.delete(
            f"/transfers/{created['transfer_uuid']}/", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 204

        assert await self._get_balance(http_client, auth_tokens, source["account_uuid"]) == 1000.00
        assert await self._get_balance(http_client, auth_tokens, destination["account_uuid"]) == 500.00

    @pytest.mark.asyncio
    async def test_create_transfer_invalid_amount(self, http_client, auth_tokens):
        source = await self._create_account(http_client, auth_tokens, "Invalid Source", 1000.00)
        destination = await self._create_account(http_client, auth_tokens, "Invalid Dest", 500.00)

        response = await http_client.post(
            "/transfers/",
            json={
                "source_account_uuid": source["account_uuid"],
                "destination_account_uuid": destination["account_uuid"],
                "amount": -50.00,
                "transfer_date": str(date.today()),
            },
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_transfer_unauthorized(self, http_client):
        response = await http_client.post(
            "/transfers/",
            json={
                "source_account_uuid": "a",
                "destination_account_uuid": "b",
                "amount": 10.00,
            },
        )
        assert response.status_code == 401
