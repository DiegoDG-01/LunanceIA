"""Llamadas HTTP compartidas por los adaptadores.

Las llaves viajan en la URL (DataBursatil, EODHD, Twelve Data), así que ningún mensaje de
error incluye la URL ni el texto de la excepción de httpx: solo el tipo de error, el código
HTTP y un fragmento de la respuesta sin la llave.
"""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import httpx

from application.interfaces.market_data import (
    ProviderName,
    ProviderUnavailable,
    QuotaExhausted,
)

DEFAULT_TIMEOUT = 20.0


class ProviderHttp:
    def __init__(
        self,
        provider: ProviderName,
        *,
        secret: str = "",
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._provider = provider
        self._secret = secret
        self._timeout = timeout
        # Para tests: `httpx.MockTransport`.
        self._transport = transport

    def snippet(self, response: httpx.Response, size: int = 200) -> str:
        text = response.text[:size].strip()
        if self._secret:
            text = text.replace(self._secret, "***")
        return text

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """GET que convierte fallas de red, 429 y 5xx en errores del puerto. El resto de los
        códigos los interpreta cada adaptador."""
        async with httpx.AsyncClient(
            timeout=self._timeout, transport=self._transport, follow_redirects=True
        ) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
            except httpx.HTTPError as error:
                raise ProviderUnavailable(
                    self._provider, f"sin respuesta: {type(error).__name__}"
                ) from None
        if response.status_code == 429:
            raise QuotaExhausted(
                self._provider,
                f"HTTP 429: {self.snippet(response)}",
                retry_after=retry_after_seconds(response, default=60),
            )
        if response.status_code >= 500:
            raise ProviderUnavailable(
                self._provider, f"HTTP {response.status_code}: {self.snippet(response)}"
            )
        return response

    def json(self, response: httpx.Response):
        try:
            return response.json()
        except ValueError:
            raise ProviderUnavailable(
                self._provider,
                f"HTTP {response.status_code}, respuesta no JSON: {self.snippet(response)}",
            ) from None


def retry_after_seconds(response: httpx.Response, *, default: int) -> int:
    value = response.headers.get("Retry-After", "")
    return int(value) if value.isdigit() and int(value) > 0 else default


def seconds_until_utc_midnight(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(1, int((midnight - now).total_seconds()))
