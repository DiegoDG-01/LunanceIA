"""End-to-end tests for transaction API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens

@pytest.mark.e2e
class TestTransactionCRUD:
    """Test transaction CRUD operations and impact on account balance."""

    @pytest.fixture
    async def test_account(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Helper fixture to create a test account."""
        account_data = {
            "name": "Transaction Test Account",
            "account_type": "CHECKING",
            "bank": "Test Bank",
            "initial_balance": 1000.00,
            "currency": "MXN"
        }
        response = await http_client.post("/account", json=account_data, headers=auth_tokens.get_auth_headers())
        return response.json()

    @pytest.mark.asyncio
    async def test_create_expense_updates_balance(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, test_account):
        """Test that creating an expense transaction correctly reduces account balance."""
        account_uuid = test_account["account_uuid"]
        initial_balance = float(test_account["current_balance"])

        transaction_data = {
            "account_uuid": account_uuid,
            "category_id": 1, # Alimentos (Expense)
            "transaction_type": "EXPENSE",
            "amount": 200.50,
            "description": "Supermarket",
            "transaction_date": "2024-01-22"
        }

        # 1. Create Transaction
        response = await http_client.post("/transaction", json=transaction_data, headers=auth_tokens.get_auth_headers())
        assert response.status_code == 200

        # 2. Verify Account Balance
        acc_response = await http_client.get(f"/account/{account_uuid}", headers=auth_tokens.get_auth_headers())
        new_balance = float(acc_response.json()["current_balance"])

        assert new_balance == initial_balance - 200.50

    @pytest.mark.asyncio
    async def test_create_income_updates_balance(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, test_account):
        """Test that creating an income transaction correctly increases account balance."""
        account_uuid = test_account["account_uuid"]
        initial_balance = float(test_account["current_balance"])

        transaction_data = {
            "account_uuid": account_uuid,
            "category_id": 2, # Salario (Income)
            "transaction_type": "INCOME",
            "amount": 500.00,
            "description": "Bonus",
            "transaction_date": "2024-01-22"
        }

        # 1. Create Transaction
        response = await http_client.post("/transaction", json=transaction_data, headers=auth_tokens.get_auth_headers())
        assert response.status_code == 200

        # 2. Verify Account Balance
        acc_response = await http_client.get(f"/account/{account_uuid}", headers=auth_tokens.get_auth_headers())
        new_balance = float(acc_response.json()["current_balance"])

        assert new_balance == initial_balance + 500.00

    @pytest.mark.asyncio
    async def test_get_transactions_list(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, test_account):
        """Test getting list of transactions."""
        account_uuid = test_account["account_uuid"]

        # Create one transaction first
        await http_client.post("/transaction", json={
            "account_uuid": account_uuid,
            "category_id": 1,
            "transaction_type": "EXPENSE",
            "amount": 50.0,
            "description": "Coffee",
            "transaction_date": "2024-01-22"
        }, headers=auth_tokens.get_auth_headers())

        response = await http_client.get("/transaction", headers=auth_tokens.get_auth_headers())
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_delete_transaction_reverts_balance(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, test_account):
        """Test that deleting a transaction reverts the impact on account balance."""
        account_uuid = test_account["account_uuid"]
        initial_balance = float(test_account["current_balance"])

        # 1. Create Expense
        create_res = await http_client.post("/transaction", json={
            "account_uuid": account_uuid,
            "category_id": 1,
            "transaction_type": "EXPENSE",
            "amount": 100.0,
            "description": "Temporary expense",
            "transaction_date": "2024-01-22"
        }, headers=auth_tokens.get_auth_headers())

        transaction_uuid = create_res.json()["uuid"]

        # 2. Delete Transaction
        del_response = await http_client.delete(f"/transaction/{transaction_uuid}", headers=auth_tokens.get_auth_headers())
        assert del_response.status_code == 204

        # 3. Verify Balance reverted to initial
        acc_response = await http_client.get(f"/account/{account_uuid}", headers=auth_tokens.get_auth_headers())
        final_balance = float(acc_response.json()["current_balance"])

        assert final_balance == initial_balance

@pytest.mark.e2e
class TestTransactionValidation:
    """Test transaction validation cases."""

    @pytest.mark.asyncio
    async def test_create_transaction_invalid_amount(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test creating transaction with negative amount fails."""
        transaction_data = {
            "account_uuid": "some-uuid",
            "category_id": 1,
            "transaction_type": "EXPENSE",
            "amount": -100.00,
            "description": "Invalid"
        }
        response = await http_client.post("/transaction", json=transaction_data, headers=auth_tokens.get_auth_headers())
        assert response.status_code == 422
