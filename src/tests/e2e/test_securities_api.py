"""Endpoints de valores: búsqueda en el catálogo y precios de cierre."""

from datetime import date
from decimal import Decimal
from typing import cast

import httpx
import pytest
from sqlalchemy import select

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
from infrastructure.database.models.transaction import TransactionModel
from main import app
from presentation.dependencies.security_deps import get_instrument_tracker, get_market_data

from ..conftest import AuthTokens
from ..idempotency import with_idempotency_key
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


@pytest.fixture
def tracked(http_client):
    """Sustituye el backfill en segundo plano (que llamaría a los proveedores reales)."""
    calls: list[tuple[int, date]] = []

    async def tracker(instrument_id: int, since: date) -> None:
        calls.append((instrument_id, since))

    app.dependency_overrides[get_instrument_tracker] = lambda: tracker
    return calls


async def _account(http_client, auth_tokens, currency="MXN", balance=10000.0):
    response = await http_client.post(
        "/account",
        json={
            "name": f"Casa de bolsa {currency}",
            "account_type": "INVESTMENT",
            "bank_id": 1,
            "initial_balance": balance,
            "currency": currency,
        },
        headers=with_idempotency_key(auth_tokens.get_auth_headers()),
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["account_uuid"]


async def _instrument(db_session, symbol="WALMEX*"):
    return await SQLAlchemyInstrumentRepository(db_session).save(
        Instrument(
            id=None,
            uuid=None,
            market=Market.BMV,
            symbol=symbol,
            name=symbol,
            instrument_type=InstrumentType.STOCK,
            currency="MXN",
        )
    )


@pytest.mark.e2e
class TestTrades:
    async def test_full_flow(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, db_session, tracked
    ):
        account_uuid = await _account(http_client, auth_tokens)
        walmex = await _instrument(db_session)
        headers = auth_tokens.get_auth_headers()

        bought = await http_client.post(
            "/securities/trades/",
            json={
                "account_uuid": account_uuid,
                "instrument_uuid": walmex.uuid,
                "trade_type": "BUY",
                "trade_date": "2026-11-03",
                "quantity": "10",
                "price": "54.79",
                "fees": "11.60",
            },
            headers=with_idempotency_key(headers),
        )
        assert bought.status_code == 201, bought.text
        body = bought.json()
        assert body["trade"]["cash_amount"] == "559.50"
        assert body["holding"]["quantity"] == "10.00000000"
        assert body["account_available_balance"] == "9440.50"
        assert tracked == [(walmex.id, date(2026, 11, 3))]

        sold = await http_client.post(
            "/securities/trades/",
            json={
                "account_uuid": account_uuid,
                "instrument_uuid": walmex.uuid,
                "trade_type": "SELL",
                "trade_date": "2026-11-05",
                "quantity": "4",
                "price": "60",
            },
            headers=with_idempotency_key(headers),
        )
        assert sold.status_code == 201, sold.text

        trades = await http_client.get(
            "/securities/trades/", params={"account_uuid": account_uuid}, headers=headers
        )
        assert [t["trade_type"] for t in trades.json()] == ["SELL", "BUY"]

        holdings = await http_client.get("/securities/holdings/", headers=headers)
        [holding] = holdings.json()
        assert holding["quantity"] == "6.00000000"
        assert holding["instrument"]["symbol"] == "WALMEX*"
        assert holding["market_value"] is None

        detail = await http_client.get(
            f"/securities/holdings/{holding['uuid']}", headers=headers
        )
        assert len(detail.json()["trades"]) == 2

        updated = await http_client.put(
            f"/securities/trades/{sold.json()['trade']['uuid']}",
            json={"trade_date": "2026-11-05", "quantity": "5", "price": "60"},
            headers=headers,
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["holding"]["quantity"] == "5.00000000"

        deleted = await http_client.delete(
            f"/securities/trades/{sold.json()['trade']['uuid']}", headers=headers
        )
        assert deleted.status_code == 200
        assert deleted.json()["trade"] is None
        assert deleted.json()["account_available_balance"] == "9440.50"

    async def test_cannot_delete_the_buy_behind_a_sale(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, db_session, tracked
    ):
        account_uuid = await _account(http_client, auth_tokens)
        walmex = await _instrument(db_session)
        headers = auth_tokens.get_auth_headers()
        uuids = []
        for payload in (
            {"trade_type": "BUY", "trade_date": "2026-11-03"},
            {"trade_type": "SELL", "trade_date": "2026-11-05"},
        ):
            response = await http_client.post(
                "/securities/trades/",
                json={
                    "account_uuid": account_uuid,
                    "instrument_uuid": walmex.uuid,
                    "quantity": "10",
                    "price": "50",
                    **payload,
                },
                headers=with_idempotency_key(headers),
            )
            assert response.status_code == 201, response.text
            uuids.append(response.json()["trade"]["uuid"])

        # La última petición de la prueba: el rollback cierra la transacción del fixture.
        refused = await http_client.delete(
            f"/securities/trades/{uuids[0]}", headers=headers
        )
        assert refused.status_code == 409
        assert refused.json()["error_code"] == "INSUFFICIENT_SHARES"

    async def test_post_requires_idempotency_key(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, tracked
    ):
        response = await http_client.post(
            "/securities/trades/",
            json={
                "account_uuid": "x",
                "instrument_uuid": "y",
                "trade_type": "BUY",
                "trade_date": "2026-11-03",
                "quantity": "1",
                "price": "1",
            },
            headers=auth_tokens.get_auth_headers(),
        )
        assert response.status_code in (400, 422)

    async def test_invalid_trade(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, db_session, tracked
    ):
        account_uuid = await _account(http_client, auth_tokens)
        walmex = await _instrument(db_session)
        response = await http_client.post(
            "/securities/trades/",
            json={
                "account_uuid": account_uuid,
                "instrument_uuid": walmex.uuid,
                "trade_type": "DIVIDEND",
                "trade_date": "2026-11-03",
                "quantity": "1",
            },
            headers=with_idempotency_key(auth_tokens.get_auth_headers()),
        )
        assert response.status_code == 400
        assert response.json()["error_code"] == "VALIDATION_INVALID_SECURITY_TRADE"
        assert tracked == []

    async def test_trade_transaction_is_locked_in_transactions(
        self, http_client: httpx.AsyncClient, auth_tokens: AuthTokens, db_session, tracked
    ):
        account_uuid = await _account(http_client, auth_tokens)
        walmex = await _instrument(db_session)
        headers = auth_tokens.get_auth_headers()
        for payload in (
            {"trade_type": "BUY", "quantity": "10", "price": "50"},
            {"trade_type": "DIVIDEND", "gross_amount": "20"},
        ):
            response = await http_client.post(
                "/securities/trades/",
                json={
                    "account_uuid": account_uuid,
                    "instrument_uuid": walmex.uuid,
                    "trade_date": "2026-11-03",
                    **payload,
                },
                headers=with_idempotency_key(headers),
            )
            assert response.status_code == 201, response.text

        model = (
            await db_session.execute(
                select(TransactionModel).where(TransactionModel.type == "INCOME")
            )
        ).scalars().first()
        response = await http_client.delete(f"/transaction/{model.uuid}/", headers=headers)
        assert response.status_code == 409
        assert response.json()["error_code"] == "SECURITY_TRADE_TRANSACTION_LOCKED"
