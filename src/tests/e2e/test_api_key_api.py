"""Tests E2E para el ciclo de vida de API keys."""

import pytest


@pytest.mark.asyncio
class TestAPIKeyLifecycle:
    async def _create_key(self, http_client, auth_tokens, scopes=None):
        response = await http_client.post(
            "/api-keys/",
            json={
                "name": "test-key",
                "scopes": scopes or ["transactions:read"],
            },
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 201
        return response.json()

    async def test_create_api_key_returns_raw_key_once(self, http_client, auth_tokens):
        created = await self._create_key(http_client, auth_tokens)

        assert created["raw_key"].startswith("moon_")
        assert created["key_prefix"] == created["raw_key"][:12]

        # El listado nunca expone raw_key ni hash
        response = await http_client.get(
            "/api-keys/", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 200
        listed = next(k for k in response.json() if k["uuid"] == created["uuid"])
        assert "raw_key" not in listed
        assert "key_hash" not in listed

    async def test_api_key_authenticates_with_scope(self, http_client, auth_tokens):
        created = await self._create_key(http_client, auth_tokens)

        response = await http_client.get(
            "/transaction/", headers={"X-API-Key": created["raw_key"]}
        )
        assert response.status_code == 200

    async def test_api_key_without_scope_is_forbidden(self, http_client, auth_tokens):
        created = await self._create_key(
            http_client, auth_tokens, scopes=["accounts:read"]
        )

        response = await http_client.get(
            "/transaction/", headers={"X-API-Key": created["raw_key"]}
        )
        assert response.status_code == 403

    async def test_missing_credentials_returns_401(self, http_client):
        response = await http_client.get("/transaction/")
        assert response.status_code == 401

    async def test_api_key_with_write_scope_creates_transaction(
        self, http_client, auth_tokens
    ):
        created = await self._create_key(
            http_client, auth_tokens, scopes=["transactions:write"]
        )

        acc_res = await http_client.post(
            "/account",
            json={
                "name": "APIKey Write Account",
                "account_type": "CHECKING",
                "bank_id": 1,
                "initial_balance": 1000.0,
                "currency": "MXN",
            },
            headers=auth_tokens.get_auth_headers(),
        )
        account_uuid = acc_res.json()["account_uuid"]

        response = await http_client.post(
            "/transaction/",
            json={
                "account_uuid": account_uuid,
                "category_id": 1,
                "transaction_type": "EXPENSE",
                "amount": 50.0,
                "description": "Compra via API key",
                "transaction_date": "2024-01-22",
            },
            headers={"X-API-Key": created["raw_key"]},
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Compra via API key"

    async def test_read_only_key_cannot_create_transaction(
        self, http_client, auth_tokens
    ):
        created = await self._create_key(
            http_client, auth_tokens, scopes=["transactions:read"]
        )

        response = await http_client.post(
            "/transaction/",
            json={
                "account_uuid": "irrelevant",
                "category_id": 1,
                "transaction_type": "EXPENSE",
                "amount": 50.0,
                "description": "No debería crearse",
                "transaction_date": "2024-01-22",
            },
            headers={"X-API-Key": created["raw_key"]},
        )
        assert response.status_code == 403

    async def test_revoked_key_stops_authenticating(self, http_client, auth_tokens):
        """Regresión A1: la revocación debe persistirse (commit) y cortar el acceso."""
        created = await self._create_key(http_client, auth_tokens)

        # La key funciona antes de revocar
        response = await http_client.get(
            "/transaction/", headers={"X-API-Key": created["raw_key"]}
        )
        assert response.status_code == 200

        # Revocar
        response = await http_client.delete(
            f"/api-keys/{created['uuid']}/", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 204

        # El listado refleja la revocación
        response = await http_client.get(
            "/api-keys/", headers=auth_tokens.get_auth_headers()
        )
        listed = next(k for k in response.json() if k["uuid"] == created["uuid"])
        assert listed["is_active"] is False

        # La key ya no autentica
        response = await http_client.get(
            "/transaction/", headers={"X-API-Key": created["raw_key"]}
        )
        assert response.status_code == 401

    async def test_revoke_unknown_key_returns_404(self, http_client, auth_tokens):
        response = await http_client.delete(
            "/api-keys/00000000-0000-0000-0000-000000000000/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404

    async def test_last_used_at_is_persisted(self, http_client, auth_tokens):
        """Regresión A1: el uso de la key debe persistir last_used_at."""
        created = await self._create_key(http_client, auth_tokens)

        response = await http_client.get(
            "/transaction/", headers={"X-API-Key": created["raw_key"]}
        )
        assert response.status_code == 200

        response = await http_client.get(
            "/api-keys/", headers=auth_tokens.get_auth_headers()
        )
        listed = next(k for k in response.json() if k["uuid"] == created["uuid"])
        assert listed["last_used_at"] is not None
