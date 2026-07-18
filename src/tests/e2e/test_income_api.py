"""End-to-end tests for recurring income API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens
from datetime import date


@pytest.mark.e2e
class TestRecurringIncomeCRUD:
    """Test recurring income management."""

    @pytest.fixture
    async def test_account(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        """Helper fixture to create a test account."""
        account_data = {
            "name": "Income Test Account",
            "account_type": "CHECKING",
            "bank_id": 1,
            "initial_balance": 5000.00,
            "currency": "MXN",
        }
        response = await http_client.post(
            "/account", json=account_data, headers=auth_tokens.get_auth_headers()
        )
        return response.json()

    @pytest.fixture
    async def created_income(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, test_account
    ):
        income_data = {
            "account_uuid": test_account["account_uuid"],
            "category_id": 1,
            "name": "Nómina Test",
            "amount": 15000.00,
            "frequency": "BIWEEKLY",
            "start_date": str(date.today()),
            "description": "Nómina quincenal",
        }
        response = await http_client.post(
            "/incomes", json=income_data, headers=auth_tokens.get_auth_headers()
        )
        return response.json()

    @pytest.mark.asyncio
    async def test_create_income_success(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, test_account
    ):
        """Test successful creation of a recurring income."""
        income_data = {
            "account_uuid": test_account["account_uuid"],
            "category_id": 1,
            "name": "Nómina Empresa X",
            "amount": 15000.00,
            "frequency": "BIWEEKLY",
            "start_date": str(date.today()),
        }

        response = await http_client.post(
            "/incomes", json=income_data, headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Nómina Empresa X"
        assert float(data["amount"]) == 15000.00
        assert data["is_active"] is True
        assert data["next_payment_date"] == str(date.today())
        assert "uuid" in data

    @pytest.mark.asyncio
    async def test_create_income_rejects_invalid_date_range(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, test_account
    ):
        """end_date before start_date must be rejected."""
        income_data = {
            "account_uuid": test_account["account_uuid"],
            "category_id": 1,
            "name": "Nómina inválida",
            "amount": 1000.00,
            "frequency": "MONTHLY",
            "start_date": "2026-07-15",
            "end_date": "2026-01-01",
        }

        response = await http_client.post(
            "/incomes", json=income_data, headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_get_incomes_list(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_income
    ):
        """Test listing user recurring incomes."""
        response = await http_client.get(
            "/incomes", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(income["uuid"] == created_income["uuid"] for income in data)

    @pytest.mark.asyncio
    async def test_get_income_by_uuid(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_income
    ):
        response = await http_client.get(
            f"/incomes/{created_income['uuid']}/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["uuid"] == created_income["uuid"]

    @pytest.mark.asyncio
    async def test_get_income_not_found(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        response = await http_client.get(
            "/incomes/00000000-0000-0000-0000-000000000000/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_income_unauthorized(self, http_client: httpx.AsyncClient):
        """Test income access without authentication."""
        response = await http_client.get("/incomes")
        assert response.status_code == 401


@pytest.mark.e2e
class TestRecurringIncomeUpdateAndState:
    @pytest.fixture
    async def created_income(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        acc_res = await http_client.post(
            "/account",
            json={
                "name": "Income Update Account",
                "account_type": "CHECKING",
                "bank_id": 1,
                "initial_balance": 5000.0,
                "currency": "MXN",
            },
            headers=auth_tokens.get_auth_headers(),
        )
        income_res = await http_client.post(
            "/incomes",
            json={
                "account_uuid": acc_res.json()["account_uuid"],
                "category_id": 1,
                "name": "Nómina Original",
                "amount": 10000.00,
                "frequency": "MONTHLY",
                "start_date": str(date.today()),
            },
            headers=auth_tokens.get_auth_headers(),
        )
        return income_res.json()

    @pytest.mark.asyncio
    async def test_update_income_success(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_income
    ):
        response = await http_client.patch(
            f"/incomes/{created_income['uuid']}/",
            json={"name": "Nómina Nueva Empresa", "amount": 18000.00},
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Nómina Nueva Empresa"
        assert float(data["amount"]) == 18000.00

    @pytest.mark.asyncio
    async def test_toggle_income_state(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_income
    ):
        response = await http_client.patch(
            f"/incomes/{created_income['uuid']}/activate/",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_income(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_income
    ):
        response = await http_client.delete(
            f"/incomes/{created_income['uuid']}/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 204

        get_response = await http_client.get(
            f"/incomes/{created_income['uuid']}/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert get_response.status_code == 404


@pytest.mark.e2e
class TestIncomeDeposits:
    @pytest.fixture
    async def created_income(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        acc_res = await http_client.post(
            "/account",
            json={
                "name": "Income Deposits Account",
                "account_type": "CHECKING",
                "bank_id": 1,
                "initial_balance": 0.0,
                "currency": "MXN",
            },
            headers=auth_tokens.get_auth_headers(),
        )
        income_res = await http_client.post(
            "/incomes",
            json={
                "account_uuid": acc_res.json()["account_uuid"],
                "category_id": 1,
                "name": "Nómina Deposits",
                "amount": 5000.00,
                "frequency": "MONTHLY",
                "start_date": str(date.today()),
            },
            headers=auth_tokens.get_auth_headers(),
        )
        return income_res.json()

    @pytest.mark.asyncio
    async def test_deposits_empty_for_new_income(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, created_income
    ):
        """A newly created income has no deposits until the job runs."""
        response = await http_client.get(
            f"/incomes/{created_income['uuid']}/deposits/",
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_deposits_of_foreign_income_not_accessible(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        response = await http_client.get(
            "/incomes/00000000-0000-0000-0000-000000000000/deposits/",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404
