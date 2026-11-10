"""End-to-end tests for dashboard API endpoints."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

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

        today_str = str(datetime.now(UTC).astimezone().date())

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
        assert set(data) == {
            "total_spent",
            "total_income",
            "total_purchases",
            "top_category",
            "top_account",
            "today_transactions",
            "category_distribution",
        }

        # The logic: 500 (income) and 200 (expense)
        assert float(data["total_income"]) == 500.00
        assert float(data["total_spent"]) == 200.00
        assert int(data["total_purchases"]) == 1
        assert data["top_category"] == "Alimentos"
        assert data["top_account"] == account_data["name"]
        assert isinstance(data["today_transactions"], list)
        assert isinstance(data["category_distribution"], list)

    @pytest.mark.asyncio
    async def test_mobile_dashboard_summary_returns_only_expense_metrics(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        """Mobile summary excludes unused fields and aggregates monthly expenses."""
        account_data = {
            "name": "Mobile Dashboard Test Account",
            "account_type": "CHECKING",
            "bank_id": 1,
            "initial_balance": 1000.00,
            "currency": "MXN",
        }
        account_response = await http_client.post(
            "/account", json=account_data, headers=auth_tokens.get_auth_headers()
        )
        assert account_response.status_code == 201
        account_uuid = account_response.json()["account_uuid"]
        today = str(datetime.now(UTC).astimezone().date())

        transactions = [
            {"category_id": 1, "transaction_type": "EXPENSE", "amount": 100.00},
            {"category_id": 1, "transaction_type": "EXPENSE", "amount": 250.00},
            {"category_id": 3, "transaction_type": "EXPENSE", "amount": 50.00},
            {"category_id": 2, "transaction_type": "INCOME", "amount": 900.00},
        ]
        for transaction in transactions:
            response = await http_client.post(
                "/transaction",
                json={
                    "account_uuid": account_uuid,
                    "description": "Mobile dashboard test transaction",
                    "transaction_date": today,
                    **transaction,
                },
                headers=auth_tokens.get_auth_headers(),
            )
            assert response.status_code == 200

        response = await http_client.get(
            "/dashboard/mobile", headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert set(data) == {
            "total_spent",
            "top_category",
            "category_distribution",
            "monthly_budget",
        }
        assert float(data["total_spent"]) == 400.00
        assert data["top_category"] == "Alimentos"
        assert data["monthly_budget"] is None

        distribution = {item["category"]: item for item in data["category_distribution"]}
        assert distribution["Alimentos"] == {
            "category": "Alimentos",
            "count": 2,
            "percent_by_count": 66.67,
        }
        assert distribution["Transporte"] == {
            "category": "Transporte",
            "count": 1,
            "percent_by_count": 33.33,
        }
        assert sum(item["percent_by_count"] for item in distribution.values()) == pytest.approx(
            100.0, abs=0.01
        )

    @pytest.mark.asyncio
    async def test_mobile_dashboard_summary_normalizes_active_budget_periods(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        """Mobile summary consolidates every active budget into the current month."""
        budgets = [
            ("semanal", 5.00),
            ("quincenal", 10.00),
            ("mensual", 100.00),
            ("trimestral", 30.00),
            ("anual", 120.00),
        ]
        for index, (period, limit_amount) in enumerate(budgets):
            response = await http_client.post(
                "/budgets/",
                json={
                    "name": f"Mobile summary budget {index}",
                    "limit_amount": limit_amount,
                    "period": period,
                },
                headers=auth_tokens.get_auth_headers(),
            )
            assert response.status_code == 201

        today = datetime.now(UTC).astimezone().date()
        month_start = today.replace(day=1)
        if month_start.month == 12:
            next_month_start = month_start.replace(
                year=month_start.year + 1, month=1
            )
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)
        last_day_of_month = next_month_start - timedelta(days=1)
        first_week_start = month_start - timedelta(days=month_start.weekday())
        last_week_start = last_day_of_month - timedelta(
            days=last_day_of_month.weekday()
        )
        weekly_cycles = (last_week_start - first_week_start).days // 7 + 1
        expected_limit = weekly_cycles * 5 + 20 + 100 + 10 + 10

        response = await http_client.get(
            "/dashboard/mobile", headers=auth_tokens.get_auth_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert data["monthly_budget"] == {
            "limit": pytest.approx(expected_limit),
            "spent": 0.0,
            "remaining": pytest.approx(expected_limit),
        }

    @pytest.mark.asyncio
    async def test_mobile_dashboard_summary_requires_authentication(
        self, http_client: httpx.AsyncClient
    ):
        response = await http_client.get("/dashboard/mobile")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dashboard_unauthorized(self, http_client: httpx.AsyncClient):
        """Test dashboard access without authentication."""
        response = await http_client.get("/dashboard")
        assert response.status_code == 401
