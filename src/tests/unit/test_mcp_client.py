"""Cliente HTTP del servidor MCP: Idempotency-Key por llamada de tool que escribe."""

from uuid import UUID

import httpx
import pytest

from presentation.mcp import client as mcp_client


@pytest.fixture
def transport(monkeypatch):
    """Sustituye el cliente compartido por uno con un transporte programable."""
    calls: list[httpx.Request] = []
    behaviour: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        action = behaviour.pop(0) if behaviour else httpx.Response(200, text="ok")
        if isinstance(action, Exception):
            raise action
        return action

    fake = httpx.AsyncClient(
        base_url="http://api.test/api/v2", transport=httpx.MockTransport(handler)
    )
    monkeypatch.setattr(mcp_client, "_client", fake)
    return calls, behaviour


@pytest.mark.unit
@pytest.mark.asyncio
class TestRequestApi:
    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    async def test_writes_send_a_uuid_idempotency_key(self, transport, method):
        calls, _ = transport

        await mcp_client.request_api(method, "/transaction/", "moon_key", json={})

        assert calls[0].headers["X-API-Key"] == "moon_key"
        UUID(calls[0].headers["Idempotency-Key"])

    async def test_reads_do_not_send_a_key(self, transport):
        calls, _ = transport

        await mcp_client.request_api("GET", "/transaction/", "moon_key")

        assert "Idempotency-Key" not in calls[0].headers

    async def test_each_tool_call_gets_a_new_key(self, transport):
        calls, _ = transport

        await mcp_client.request_api("POST", "/transaction/", "moon_key", json={})
        await mcp_client.request_api("POST", "/transaction/", "moon_key", json={})

        assert calls[0].headers["Idempotency-Key"] != calls[1].headers["Idempotency-Key"]

    async def test_retry_after_lost_response_reuses_the_key(self, transport):
        calls, behaviour = transport
        behaviour.append(httpx.ReadTimeout("no response"))

        result = await mcp_client.request_api(
            "POST", "/transaction/", "moon_key", json={"amount": 10}
        )

        assert result == "ok"
        assert len(calls) == 2
        assert calls[0].headers["Idempotency-Key"] == calls[1].headers["Idempotency-Key"]
        assert calls[0].content == calls[1].content

    async def test_gives_up_after_max_attempts(self, transport):
        calls, behaviour = transport
        behaviour.extend(
            [httpx.ConnectError("down")] * mcp_client.MAX_ATTEMPTS
        )

        result = await mcp_client.request_api("POST", "/transaction/", "moon_key")

        assert result.startswith("No se pudo conectar con la API")
        assert len(calls) == mcp_client.MAX_ATTEMPTS

    async def test_http_errors_are_not_retried(self, transport):
        calls, behaviour = transport
        behaviour.append(
            httpx.Response(422, json={"error_code": "IDEMPOTENCY_KEY_REUSED"})
        )

        result = await mcp_client.request_api("POST", "/transaction/", "moon_key")

        assert result.startswith("Error 422")
        assert len(calls) == 1
