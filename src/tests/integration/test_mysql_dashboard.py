"""Dashboard por moneda contra MySQL 8 real.

El dashboard dejó el SQL crudo de MySQL por consultas de SQLAlchemy que corren igual en
SQLite: aquí se comprueba que en MySQL dan lo mismo. Arranca un `mysql:8.0` desechable con
Docker; si Docker no está disponible, se salta.

    uv run pytest -q -m integration src/tests/integration/test_mysql_dashboard.py
"""

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from ..idempotency import with_idempotency_key
from ..isolated_app import bearer, isolated_app
from .test_mysql_idempotency import mysql_url  # noqa: F401 - fixture de módulo

pytestmark = pytest.mark.integration

TODAY = str(date.today())


@pytest_asyncio.fixture
async def api(mysql_url):  # noqa: F811
    engine = create_async_engine(mysql_url, pool_size=5, max_overflow=0)
    try:
        async with isolated_app(engine) as harness:
            yield harness
    finally:
        await engine.dispose()


async def _post(api, path: str, body: dict) -> dict:
    response = await api.client.post(
        path, json=body, headers=with_idempotency_key(bearer())
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


async def test_totals_are_split_by_currency(api):
    accounts = {}
    for currency in ("MXN", "USD"):
        body = await _post(
            api,
            "/account",
            {
                "name": f"Cuenta {currency}",
                "account_type": "CHECKING",
                "bank_id": 1,
                "initial_balance": 1000,
                "currency": currency,
            },
        )
        accounts[currency] = body["account_uuid"]
    for currency, kind, amount, category in (
        ("MXN", "EXPENSE", 200, 1),
        ("USD", "EXPENSE", 50, 1),
        ("USD", "EXPENSE", 30, 1),
        ("USD", "INCOME", 100, 2),
    ):
        await _post(
            api,
            "/transaction",
            {
                "account_uuid": accounts[currency],
                "category_id": category,
                "transaction_type": kind,
                "amount": amount,
                "transaction_date": TODAY,
            },
        )
    for currency, limit, period in (("MXN", 1000, "mensual"), ("USD", 1200, "anual")):
        await _post(
            api,
            "/budgets/",
            {"name": currency, "limit_amount": limit, "period": period, "currency": currency},
        )

    web = (await api.client.get("/dashboard/", headers=bearer())).json()
    assert (web["total_spent"], web["total_income"], web["total_purchases"]) == (200.0, 0.0, 1)
    usd = {c["currency"]: c for c in web["by_currency"]}["USD"]
    assert (usd["total_spent"], usd["total_income"], usd["total_purchases"]) == (80.0, 100.0, 2)
    assert sorted(t["amount"] for t in usd["today_transactions"]) == [30.0, 50.0]
    assert usd["category_distribution"] == [
        {"category": "Alimentos", "count": 2, "percent_by_count": 100.0}
    ]

    mobile = (await api.client.get("/dashboard/mobile/", headers=bearer())).json()
    assert mobile["monthly_budget"] == {"limit": 1000.0, "spent": 200.0, "remaining": 800.0}
    usd = {c["currency"]: c for c in mobile["by_currency"]}["USD"]
    # Un presupuesto anual de 1,200 es de 100 al mes.
    assert usd["monthly_budget"] == {"limit": 100.0, "spent": 80.0, "remaining": 20.0}
