"""Totales por moneda: el dashboard y los presupuestos no suman monedas distintas."""

from datetime import date

import pytest

from ..idempotency import with_idempotency_key

TODAY = str(date.today())
FOOD, TRANSPORT = 1, 3


@pytest.fixture
async def setup(http_client, auth_tokens):
    """Pesos: un gasto de 200. Dólares: gastos de 50 y 30 y un ingreso de 100."""
    headers = auth_tokens.get_auth_headers()

    async def post(path, body):
        response = await http_client.post(
            path, json=body, headers=with_idempotency_key(headers)
        )
        assert response.status_code in (200, 201), response.text
        return response.json()

    async def account(currency):
        body = await post(
            "/account",
            {
                "name": f"Cuenta {currency}",
                "account_type": "CHECKING",
                "bank_id": 1,
                "initial_balance": 1000,
                "currency": currency,
            },
        )
        return body["account_uuid"]

    async def movement(account_uuid, kind, amount, category):
        await post(
            "/transaction",
            {
                "account_uuid": account_uuid,
                "category_id": category,
                "transaction_type": kind,
                "amount": amount,
                "transaction_date": TODAY,
            },
        )

    pesos, dollars = await account("MXN"), await account("USD")
    await movement(pesos, "EXPENSE", 200, FOOD)
    await movement(dollars, "EXPENSE", 50, FOOD)
    await movement(dollars, "EXPENSE", 30, TRANSPORT)
    await movement(dollars, "INCOME", 100, 2)
    return post, headers


@pytest.mark.e2e
@pytest.mark.asyncio
class TestDashboardByCurrency:
    async def test_web(self, http_client, setup):
        _, headers = setup
        data = (await http_client.get("/dashboard/", headers=headers)).json()

        # Los campos de siempre son solo pesos.
        assert (data["total_spent"], data["total_income"], data["total_purchases"]) == (
            200.0,
            0.0,
            1,
        )
        assert {t["currency"] for t in data["today_transactions"]} == {"MXN"}

        by_currency = {c["currency"]: c for c in data["by_currency"]}
        assert list(by_currency) == ["MXN", "USD"]
        usd = by_currency["USD"]
        assert (usd["total_spent"], usd["total_income"], usd["total_purchases"]) == (
            80.0,
            100.0,
            2,
        )
        assert usd["top_account"] == "Cuenta USD"
        assert sorted(t["amount"] for t in usd["today_transactions"]) == [30.0, 50.0]
        assert {t["currency"] for t in usd["today_transactions"]} == {"USD"}
        assert sorted(d["count"] for d in usd["category_distribution"]) == [1, 1]
        assert by_currency["MXN"]["total_spent"] == data["total_spent"]

    async def test_mobile_with_budgets_per_currency(self, http_client, setup):
        post, headers = setup
        for currency, limit in (("MXN", 1000), ("usd", 100)):
            await post(
                "/budgets/",
                {
                    "name": f"Mes {currency}",
                    "limit_amount": limit,
                    "period": "mensual",
                    "currency": currency,
                },
            )

        data = (await http_client.get("/dashboard/mobile/", headers=headers)).json()

        assert data["total_spent"] == 200.0
        assert data["monthly_budget"] == {"limit": 1000.0, "spent": 200.0, "remaining": 800.0}
        usd = {c["currency"]: c for c in data["by_currency"]}["USD"]
        assert usd["total_spent"] == 80.0
        assert usd["monthly_budget"] == {"limit": 100.0, "spent": 80.0, "remaining": 20.0}


@pytest.mark.e2e
@pytest.mark.asyncio
class TestBudgetCurrency:
    async def test_progress_counts_only_its_currency(self, http_client, setup):
        post, headers = setup
        dollars = await post(
            "/budgets/",
            {"name": "Comida USD", "limit_amount": 100, "period": "mensual", "currency": "usd"},
        )
        pesos = await post(
            "/budgets/", {"name": "Comida", "limit_amount": 500, "period": "mensual"}
        )
        assert (dollars["currency"], pesos["currency"]) == ("USD", "MXN")

        for budget, spent in ((dollars, "80.00"), (pesos, "200.00")):
            progress = await http_client.get(
                f"/budgets/{budget['uuid']}/progress/", headers=headers
            )
            assert progress.status_code == 200, progress.text
            assert (progress.json()["currency"], progress.json()["spent_amount"]) == (
                budget["currency"],
                spent,
            )

        changed = await http_client.patch(
            f"/budgets/{pesos['uuid']}/",
            json={"currency": "EUR"},
            headers=with_idempotency_key(headers),
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["currency"] == "EUR"

    async def test_other_currencies_are_rejected(self, http_client, auth_tokens):
        response = await http_client.post(
            "/budgets/",
            json={"name": "Libras", "limit_amount": 100, "period": "mensual", "currency": "GBP"},
            headers=with_idempotency_key(auth_tokens.get_auth_headers()),
        )
        assert response.status_code == 422, response.text
        assert [d["loc"][-1] for d in response.json()["details"]] == ["currency"]
