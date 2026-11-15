"""Herramientas MCP de acciones y portafolio: a qué ruta llaman y qué mandan."""

from typing import cast

import pytest
from mcp.server.mcpserver import Context

from presentation.mcp import server

TRADE = "7d3f6a52-3c1e-4f1b-9a51-0c2c8f0e9b11"
ACCOUNT = "0b8f2c1e-5d6a-4e7b-8c9d-1a2b3c4d5e6f"
INSTRUMENT = "5e6f7a8b-9c0d-4e1f-a2b3-c4d5e6f7a8b9"
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
class TestSecuritiesTools:
    async def test_record_trade_sends_only_the_given_fields(self, calls):
        await server.record_security_trade(
            CTX,
            account_uuid=ACCOUNT,
            instrument_uuid=INSTRUMENT,
            trade_type="BUY",
            trade_date="2026-11-13",
            quantity=10,
            price=56.5,
        )
        [(method, path, kwargs)] = calls
        assert (method, path) == ("POST", "/securities/trades/")
        assert kwargs["json"] == {
            "account_uuid": ACCOUNT,
            "instrument_uuid": INSTRUMENT,
            "trade_type": "BUY",
            "trade_date": "2026-11-13",
            "quantity": 10,
            "price": 56.5,
        }

    async def test_invalid_uuid_does_not_call_the_api(self, calls):
        result = await server.delete_security_trade(CTX, trade_uuid="nope")
        assert "trade_uuid" in result and calls == []

    async def test_history_passes_the_range_with_api_names(self, calls):
        await server.get_portfolio_history(CTX, from_date="2026-01-01")
        [(method, path, kwargs)] = calls
        assert (method, path) == ("GET", "/securities/portfolio/history")
        assert kwargs["params"] == {"from": "2026-01-01"}

    async def test_update_trade_uses_put(self, calls):
        await server.update_security_trade(
            CTX, trade_uuid=TRADE, trade_date="2026-11-13", gross_amount=120
        )
        [(method, path, kwargs)] = calls
        assert (method, path) == ("PUT", f"/securities/trades/{TRADE}")
        assert kwargs["json"] == {"trade_date": "2026-11-13", "gross_amount": 120}
