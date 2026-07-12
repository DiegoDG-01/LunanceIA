"""End-to-end tests for installment purchases API endpoints."""

from datetime import date

import pytest
import httpx

from ..conftest import AuthTokens


@pytest.mark.e2e
class TestInstallmentCRUD:
    """Test /installments/ endpoints."""

    @pytest.fixture
    async def test_account(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        response = await http_client.post(
            "/account",
            json={
                "name": "Installment Test Account",
                "account_type": "CREDIT_CARD",
                "bank_id": 1,
                "initial_balance": 100000.00,
                "currency": "MXN",
                "credit_card_settings": {
                    "billing_cycle_day": 15,
                    "payment_due_day": 5,
                    "credit_limit": 100000.00,
                    "minimum_payment_percentage": 5,
                },
            },
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 201, response.text
        return response.json()

    async def _create_purchase(
        self,
        http_client: httpx.AsyncClient,
        auth_tokens: AuthTokens,
        account_uuid: str,
        **overrides,
    ) -> httpx.Response:
        payload = {
            "account_uuid": account_uuid,
            "category_id": 1,
            "description": "Laptop a meses",
            "total_amount": 12000.00,
            "num_installments": 12,
            "installment_type": "NO_INTEREST",
            "annual_interest_rate": 0,
            "purchase_date": str(date.today()),
        }
        payload.update(overrides)
        return await http_client.post(
            "/installments/", json=payload, headers=auth_tokens.get_auth_headers()
        )

    @pytest.mark.asyncio
    async def test_create_purchase_generates_charges(self, http_client, auth_tokens, test_account):
        response = await self._create_purchase(
            http_client, auth_tokens, test_account["account_uuid"]
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["description"] == "Laptop a meses"
        assert float(data["total_amount"]) == 12000.00
        assert data["num_installments"] == 12
        assert len(data["charges"]) == 12
        assert float(data["monthly_payment"]) == 1000.00
        assert all(charge["paid"] is False for charge in data["charges"])

    @pytest.mark.asyncio
    async def test_create_purchase_invalid_installments(self, http_client, auth_tokens, test_account):
        response = await self._create_purchase(
            http_client, auth_tokens, test_account["account_uuid"], num_installments=1
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_purchases_list(self, http_client, auth_tokens, test_account):
        await self._create_purchase(
            http_client, auth_tokens, test_account["account_uuid"], description="Compra en lista"
        )

        response = await http_client.get(
            "/installments/", headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200
        descriptions = [p["description"] for p in response.json()]
        assert "Compra en lista" in descriptions

    @pytest.mark.asyncio
    async def test_pay_installment_charge(self, http_client, auth_tokens, test_account):
        created = (
            await self._create_purchase(http_client, auth_tokens, test_account["account_uuid"])
        ).json()
        first_charge = created["charges"][0]

        response = await http_client.post(
            f"/installments/{first_charge['uuid']}/pay/",
            json={"payment_date": str(date.today())},
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["uuid"] == first_charge["uuid"]
        assert data["paid"] is True
        assert data["paid_at"] is not None

    @pytest.mark.asyncio
    async def test_pay_unknown_charge_returns_404(self, http_client, auth_tokens):
        response = await http_client.post(
            "/installments/00000000-0000-0000-0000-000000000000/pay/",
            json={"payment_date": str(date.today())},
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_purchase(self, http_client, auth_tokens, test_account):
        created = (
            await self._create_purchase(http_client, auth_tokens, test_account["account_uuid"])
        ).json()

        response = await http_client.patch(
            f"/installments/{created['uuid']}/",
            json={"description": "Laptop gamer a meses", "notes": "Promoción Buen Fin"},
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Laptop gamer a meses"
        assert data["notes"] == "Promoción Buen Fin"

    @pytest.mark.asyncio
    async def test_delete_purchase(self, http_client, auth_tokens, test_account):
        created = (
            await self._create_purchase(http_client, auth_tokens, test_account["account_uuid"])
        ).json()

        response = await http_client.delete(
            f"/installments/{created['uuid']}/", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 204

        response = await http_client.get(
            "/installments/", headers=auth_tokens.get_auth_headers()
        )
        assert created["uuid"] not in [p["uuid"] for p in response.json()]

    @pytest.mark.asyncio
    async def test_get_purchases_unauthorized(self, http_client):
        response = await http_client.get("/installments/")
        assert response.status_code == 401
