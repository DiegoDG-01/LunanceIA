"""End-to-end tests for dashboard API endpoints."""

import pytest
import httpx
from ..conftest import AuthTokens

@pytest.mark.e2e
class TestDashboardAPI:
    """Test dashboard metrics and summary accuracy."""

    @pytest.mark.asyncio
    async def test_dashboard_summary_reflects_transactions(self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens):
        """Test that dashboard summary correctly aggregates incomes and expenses."""

        # 1. Create a test account
        account_data = {
            "name": "Dashboard Test Account",
            "account_type": "CHECKING",
            "bank_id": 1,
            "initial_balance": 1000.00,
            "currency": "MXN"
        }
        acc_res = await http_client.post("/account", json=account_data, headers=auth_tokens.get_auth_headers())
        account_uuid = acc_res.json()["account_uuid"]

        from datetime import date
        today_str = str(date.today())

        # 2. Add an Income (Category 2: Salario)
        await http_client.post("/transaction", json={
            "account_uuid": account_uuid,
            "category_id": 2,
            "transaction_type": "INCOME",
            "amount": 500.00,
            "description": "Income 1",
            "transaction_date": today_str
        }, headers=auth_tokens.get_auth_headers())

        # 3. Add an Expense (Category 1: Alimentos)
        await http_client.post("/transaction", json={
            "account_uuid": account_uuid,
            "category_id": 1,
            "transaction_type": "EXPENSE",
            "amount": 200.00,
            "description": "Expense 1",
            "transaction_date": today_str
        }, headers=auth_tokens.get_auth_headers())

        # 4. Get Dashboard Data
        response = await http_client.get("/dashboard", headers=auth_tokens.get_auth_headers())
        assert response.status_code == 200

        data = response.json()

        # Verify structure and values
        assert "total_spent" in data
        assert "total_income" in data
        assert "total_purchases" in data

        # The logic: 500 (income) and 200 (expense)
        assert float(data["total_income"]) == 500.00
        assert float(data["total_spent"]) == 200.00
        assert int(data["total_purchases"]) == 1

    @pytest.mark.asyncio
    async def test_dashboard_unauthorized(self, http_client: httpx.AsyncClient):
        """Test dashboard access without authentication."""
        response = await http_client.get("/dashboard")
        assert response.status_code == 401
