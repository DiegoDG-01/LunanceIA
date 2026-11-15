"""Monedas aceptadas al crear cuentas y apartados: MXN, USD y EUR."""

import httpx
import pytest

from ..conftest import AuthTokens
from ..idempotency import with_idempotency_key


async def _create_account(client: httpx.AsyncClient, tokens: AuthTokens, currency):
    return await client.post(
        "/account",
        json={
            "name": f"Cuenta {currency}",
            "account_type": "CHECKING",
            "bank_id": 1,
            "initial_balance": 1000,
            "currency": currency,
        },
        headers=with_idempotency_key(tokens.get_auth_headers()),
    )


@pytest.mark.e2e
@pytest.mark.asyncio
class TestAccountCurrency:
    @pytest.mark.parametrize(("sent", "saved"), [("USD", "USD"), ("eur", "EUR"), (" usd ", "USD")])
    async def test_supported_currencies_are_saved_in_uppercase(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, sent, saved
    ):
        response = await _create_account(http_client, auth_tokens, sent)
        assert response.status_code == 201, response.text
        account = await http_client.get(
            f"/account/{response.json()['account_uuid']}",
            headers=auth_tokens.get_auth_headers(),
        )
        assert account.json()["currency"] == saved

    async def test_defaults_to_pesos(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        response = await http_client.post(
            "/account",
            json={"name": "Pesos", "account_type": "CASH", "bank_id": 1},
            headers=with_idempotency_key(auth_tokens.get_auth_headers()),
        )
        assert response.status_code == 201, response.text
        assert response.json()["currency"] == "MXN"

    @pytest.mark.parametrize("currency", ["GBP", "zzz", "", 840])
    async def test_other_currencies_are_rejected(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, currency
    ):
        response = await _create_account(http_client, auth_tokens, currency)
        assert response.status_code == 422, response.text
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert [d["loc"][-1] for d in body["details"]] == ["currency"]


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPositionCurrency:
    async def test_unsupported_currency_is_rejected(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        account = await _create_account(http_client, auth_tokens, "MXN")
        response = await http_client.post(
            "/positions/",
            json={
                "account_uuid": account.json()["account_uuid"],
                "name": "Apartado",
                "position_type": "ON_DEMAND",
                "amount": 100,
                "annual_rate": 10,
                "currency": "GBP",
            },
            headers=with_idempotency_key(auth_tokens.get_auth_headers()),
        )
        assert response.status_code == 422, response.text
        assert [d["loc"][-1] for d in response.json()["details"]] == ["currency"]
