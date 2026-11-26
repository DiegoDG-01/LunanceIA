"""Herramientas MCP de cuentas, dashboard, suscripciones e ingresos: ruta y lo que mandan."""

from typing import cast

import pytest
from mcp.server.mcpserver import Context

from presentation.mcp import server

ACCOUNT = "0b8f2c1e-5d6a-4e7b-8c9d-1a2b3c4d5e6f"
SUBSCRIPTION = "7d3f6a52-3c1e-4f1b-9a51-0c2c8f0e9b11"
INCOME = "5e6f7a8b-9c0d-4e1f-a2b3-c4d5e6f7a8b9"
# Las tools solo pasan el contexto a `get_api_key`, que la prueba reemplaza.
CTX = cast(Context, None)


@pytest.fixture
def calls(monkeypatch):
    sent: list[tuple[str, str, dict]] = []

    async def fake_request(method, path, api_key, **kwargs):
        sent.append((method, path, kwargs))
        return "ok"

    monkeypatch.setattr(server, "request_api", fake_request)
    monkeypatch.setattr(server, "get_api_key", lambda ctx: "moon_key")
    return sent


@pytest.mark.unit
@pytest.mark.asyncio
class TestNewTools:
    async def test_monthly_summary_reads_the_mobile_dashboard(self, calls):
        await server.get_monthly_summary(CTX)
        assert [(m, p) for m, p, _ in calls] == [("GET", "/dashboard/mobile")]

    async def test_get_income(self, calls):
        await server.get_income(CTX, income_uuid=INCOME)
        assert [(m, p) for m, p, _ in calls] == [("GET", f"/incomes/{INCOME}/")]

    async def test_subscription_last_charge(self, calls):
        await server.get_subscription_last_charge(CTX, subscription_uuid=SUBSCRIPTION)
        assert [(m, p) for m, p, _ in calls] == [
            ("GET", f"/subscription/{SUBSCRIPTION}/transactions/")
        ]

    @pytest.mark.parametrize(
        "tool, field",
        [
            (server.get_income, "income_uuid"),
            (server.get_subscription_last_charge, "subscription_uuid"),
        ],
    )
    async def test_invalid_uuid_does_not_call_the_api(self, calls, tool, field):
        result = await tool(CTX, "nope")
        assert field in result and calls == []

    async def test_list_accounts_can_hide_inactive(self, calls):
        await server.list_accounts(CTX, only_active=True)
        [(_, path, kwargs)] = calls
        assert path == "/account"
        assert kwargs["params"] == {"only_active": True, "limit": 50, "offset": 0}


@pytest.mark.unit
@pytest.mark.asyncio
class TestUpdateAccountCardSettings:
    async def test_sends_the_four_settings_together(self, calls):
        await server.update_account(
            CTX,
            account_uuid=ACCOUNT,
            name="Oro",
            billing_cycle_day=15,
            payment_due_day=5,
            credit_limit=50000,
            minimum_payment_percentage=5,
        )
        [(method, path, kwargs)] = calls
        assert (method, path) == ("PATCH", f"/account/{ACCOUNT}/")
        assert kwargs["json"] == {
            "name": "Oro",
            "credit_card_settings": {
                "billing_cycle_day": 15,
                "payment_due_day": 5,
                "credit_limit": 50000,
                "minimum_payment_percentage": 5,
            },
        }

    async def test_partial_settings_are_rejected_before_calling(self, calls):
        result = await server.update_account(
            CTX, account_uuid=ACCOUNT, credit_limit=80000
        )
        assert "billing_cycle_day" in result and "credit_limit" not in result
        assert calls == []

    async def test_without_settings_only_the_given_fields(self, calls):
        await server.update_account(CTX, account_uuid=ACCOUNT, name="Nómina")
        [(_, _, kwargs)] = calls
        assert kwargs["json"] == {"name": "Nómina"}
