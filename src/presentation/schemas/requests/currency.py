"""Tipo de campo para monedas en los requests."""

from typing import Annotated, Any

from pydantic import BeforeValidator

from domain.objects.enums import Currency


def _normalize(value: Any) -> Any:
    # " usd " y "usd" valen como "USD"; lo que no sea texto lo rechaza el enum.
    return value.strip().upper() if isinstance(value, str) else value


# MXN, USD o EUR, sin importar mayúsculas. Otra moneda → 422 con el campo `currency`.
CurrencyCode = Annotated[Currency, BeforeValidator(_normalize)]
