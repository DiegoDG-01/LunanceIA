"""Endpoints de valores: búsqueda en el catálogo y precios de cierre."""

from datetime import date
from decimal import Decimal
from typing import cast

import httpx
import pytest

from application.interfaces.market_data import InstrumentListing, ProviderName
from domain.entities.securities.instrument import Instrument
from domain.entities.securities.instrument_price import InstrumentPrice
from domain.objects.enums import InstrumentType, Market
from infrastructure.database.repositories.sqlalchemy_instrument_repository import (
    SQLAlchemyInstrumentRepository,
)
from infrastructure.database.repositories.sqlalchemy_price_repository import (
    SQLAlchemyInstrumentPriceRepository,
)
from main import app
from presentation.dependencies.security_deps import get_market_data

from ..conftest import AuthTokens
from ..unit.application.securities.fakes import FakeGateway


@pytest.fixture
def gateway(http_client):
    fake = FakeGateway(
        catalogs={
            Market.BMV: [
                InstrumentListing(
                    market=Market.BMV,
                    symbol="WALMEX*",
                    name="WAL - MART DE MEXICO",
                    instrument_type=InstrumentType.STOCK,
                    currency="MXN",
                    isin="MX01WA000038",
                    exchange="BMV",
                )
            ]
        }
    )
    app.dependency_overrides[get_market_data] = lambda: fake
    return fake


@pytest.mark.e2e
class TestSearch:
    async def test_search_downloads_the_catalog(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, gateway
    ):
        response = await http_client.get(
            "/securities/search",
            params={"q": "walmex", "market": "BMV"},
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 200, response.text
        [walmex] = response.json()
        assert walmex["symbol"] == "WALMEX*"
        assert walmex["instrument_type"] == "STOCK"
        assert walmex["currency"] == "MXN"
        assert gateway.catalog_calls == [Market.BMV]

    async def test_query_is_required(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, gateway
    ):
        response = await http_client.get(
            "/securities/search", headers=auth_tokens.get_auth_headers()
        )
        assert response.status_code == 422

    async def test_requires_auth(self, http_client: httpx.AsyncClient, gateway):
        response = await http_client.get("/securities/search", params={"q": "x"})
        assert response.status_code == 401


@pytest.mark.e2e
class TestPrices:
    async def test_returns_stored_closes(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, db_session
    ):
        instrument = await SQLAlchemyInstrumentRepository(db_session).save(
            Instrument(
                id=None,
                uuid=None,
                market=Market.BMV,
                symbol="FUNO11",
                name="FIBRA UNO",
                instrument_type=InstrumentType.FIBRA,
                currency="MXN",
                tracked_since=date(2026, 11, 9),
            )
        )
        await SQLAlchemyInstrumentPriceRepository(db_session).save_many(
            [
                InstrumentPrice(
                    instrument_id=cast(int, instrument.id),
                    price_date=date(2026, 11, d),
                    close=Decimal(v),
                    provider=ProviderName.DATABURSATIL.value,
                )
                for d, v in ((12, "37.20"), (13, "36.68"))
            ]
        )

        response = await http_client.get(
            f"/securities/instruments/{instrument.uuid}/prices",
            params={"from": "2026-11-01", "to": "2026-11-13"},
            headers=auth_tokens.get_auth_headers(),
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["instrument"]["symbol"] == "FUNO11"
        assert [(p["price_date"], p["close"]) for p in body["prices"]] == [
            ("2026-11-12", "37.200000"),
            ("2026-11-13", "36.680000"),
        ]

    async def test_unknown_instrument(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        response = await http_client.get(
            "/securities/instruments/00000000-0000-0000-0000-000000000000/prices",
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "NOT_FOUND_INSTRUMENT"

    async def test_inverted_range(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens
    ):
        response = await http_client.get(
            "/securities/instruments/x/prices",
            params={"from": "2026-11-13", "to": "2026-11-01"},
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code == 400
