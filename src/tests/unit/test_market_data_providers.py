"""Adaptadores de precios con `httpx.MockTransport`. Las respuestas copian las formas reales
que dieron los proveedores al probarlos (2026-11-14)."""

from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest

from application.interfaces.market_data import (
    ProviderUnavailable,
    QuotaExhausted,
    SymbolNotSupported,
)
from domain.objects.enums import InstrumentType, Market
from infrastructure.external_services.market_data.banxico import BanxicoFxProvider
from infrastructure.external_services.market_data.databursatil import (
    DataBursatilProvider,
)
from infrastructure.external_services.market_data.eodhd import EodhdProvider
from infrastructure.external_services.market_data.provider_http import (
    seconds_until_utc_midnight,
)
from infrastructure.external_services.market_data.twelvedata import TwelveDataProvider
from infrastructure.external_services.market_data.yahoo import YahooProvider

SECRET = "s3cr3t-key-value"
START = date(2026, 11, 2)
END = date(2026, 11, 13)


class Recorder:
    """Transport que responde con `handler` y guarda las peticiones."""

    def __init__(self, handler):
        self.requests: list[httpx.Request] = []
        self._handler = handler

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


def respond(status=200, body=None, *, text=None, headers=None):
    def handler(_request):
        if text is not None:
            return httpx.Response(status, text=text, headers=headers)
        return httpx.Response(status, json=body, headers=headers)

    return Recorder(handler)


def network_error():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    return Recorder(handler)


def assert_no_secret(error: Exception) -> None:
    assert SECRET not in str(error)
    assert SECRET not in getattr(error, "detail", "")


# ------------------------------------------------------------------ DataBursatil


class TestDataBursatil:
    def provider(self, recorder):
        return DataBursatilProvider(token=SECRET, transport=recorder.transport)

    async def test_parses_list_format_and_marks_holidays(self):
        recorder = respond(
            body={
                "2026-11-03": [54.10, 298000000.5],
                "2026-11-02": [53.90, 0],  # feriado BMV: cierre anterior, importe 0
                "2026-11-13": [54.79, 309468263.57],
            }
        )
        closes = await self.provider(recorder).fetch_daily_closes("WALMEX*", START, END)

        assert [c.price_date for c in closes] == [
            date(2026, 11, 2),
            date(2026, 11, 3),
            date(2026, 11, 13),
        ]
        assert closes[0].is_trading_day is False
        assert closes[1].is_trading_day is True
        assert closes[2].close == Decimal("54.79")
        assert closes[2].traded_value == Decimal("309468263.57")
        params = recorder.last.url.params
        assert params["emisora_serie"] == "WALMEX*"
        assert params["inicio"] == "2026-11-02"
        assert params["final"] == "2026-11-13"

    async def test_drops_days_outside_the_range(self):
        recorder = respond(body={"2026-10-30": [1, 1], "2026-11-05": [2, 1]})
        closes = await self.provider(recorder).fetch_daily_closes("X*", START, END)
        assert [c.price_date for c in closes] == [date(2026, 11, 5)]

    async def test_unknown_symbol_is_not_supported(self):
        recorder = respond(
            400,
            {"Error": "Emisora y/o serie desconocida. Tambien puedes consultar ..."},
        )
        with pytest.raises(SymbolNotSupported):
            await self.provider(recorder).fetch_daily_closes("ZZZQX*", START, END)

    async def test_range_without_results_is_empty(self):
        recorder = respond(
            400, {"Error": "La busqueda no arrojo ningun resultado. ¿Dudas? ..."}
        )
        closes = await self.provider(recorder).fetch_daily_closes(
            "WALMEX*", date(2026, 11, 7), date(2026, 11, 8)
        )
        assert closes == []

    async def test_invalid_token_is_unavailable_without_leaking_it(self):
        recorder = respond(400, {"Error": {"token": ["Longitud del token no valida."]}})
        with pytest.raises(ProviderUnavailable) as caught:
            await self.provider(recorder).fetch_daily_closes("WALMEX*", START, END)
        assert_no_secret(caught.value)

    async def test_network_error_does_not_leak_the_token(self):
        with pytest.raises(ProviderUnavailable) as caught:
            await self.provider(network_error()).fetch_daily_closes(
                "WALMEX*", START, END
            )
        assert "ConnectError" in caught.value.detail
        assert_no_secret(caught.value)

    async def test_remaining_credits(self):
        recorder = respond(body={"disponibles": 199462})
        assert await self.provider(recorder).remaining_credits() == 199462

    def test_symbol_is_used_as_is(self):
        provider = DataBursatilProvider(token=SECRET)
        assert provider.provider_symbol(Market.BMV, "FUNO11") == "FUNO11"
        assert provider.provider_symbol(Market.SIC, "AAPL*") == "AAPL*"


# ------------------------------------------------------------------------ EODHD


class TestEodhd:
    def provider(self, recorder):
        return EodhdProvider(api_key=SECRET, transport=recorder.transport)

    def test_symbol_translation(self):
        provider = EodhdProvider(api_key=SECRET)
        assert provider.provider_symbol(Market.BMV, "WALMEX*") == "WALMEX.MX"
        assert provider.provider_symbol(Market.BMV, "FUNO11") == "FUNO11.MX"
        assert provider.provider_symbol(Market.SIC, "IVV*") == "IVV.MX"
        assert provider.provider_symbol(Market.US, "AAPL") == "AAPL.US"
        assert provider.provider_symbol(Market.US, "BRK.B") == "BRK-B.US"

    async def test_parses_unadjusted_close(self):
        recorder = respond(
            body=[
                {
                    "date": "2026-11-13",
                    "open": 6600,
                    "close": 6595.15,
                    "adjusted_close": 6590.1,
                    "volume": 120,
                },
                {"date": "2026-11-12", "close": 6580.0},
                {"date": "2026-11-11", "close": None},
            ]
        )
        closes = await self.provider(recorder).fetch_daily_closes("AAPL.MX", START, END)
        assert [(c.price_date, c.close) for c in closes] == [
            (date(2026, 11, 12), Decimal("6580.0")),
            (date(2026, 11, 13), Decimal("6595.15")),
        ]
        assert recorder.last.url.path == "/api/eod/AAPL.MX"
        assert recorder.last.url.params["from"] == "2026-11-02"
        assert recorder.last.url.params["to"] == "2026-11-13"

    async def test_unknown_ticker(self):
        recorder = respond(404, text="Ticker Not Found.")
        with pytest.raises(SymbolNotSupported):
            await self.provider(recorder).fetch_daily_closes("ZZZQX.MX", START, END)

    async def test_daily_limit_is_quota_until_midnight(self):
        recorder = respond(402, text="You exceeded your daily API requests limit.")
        with pytest.raises(QuotaExhausted) as caught:
            await self.provider(recorder).fetch_daily_closes("AAPL.US", START, END)
        assert 0 < caught.value.retry_after <= 86400

    async def test_server_error_is_unavailable(self):
        recorder = respond(503, text=f"upstream down {SECRET}")
        with pytest.raises(ProviderUnavailable) as caught:
            await self.provider(recorder).fetch_daily_closes("AAPL.US", START, END)
        assert_no_secret(caught.value)

    async def test_http_429_is_quota(self):
        recorder = respond(429, text="Too Many Requests", headers={"Retry-After": "30"})
        with pytest.raises(QuotaExhausted) as caught:
            await self.provider(recorder).fetch_daily_closes("AAPL.US", START, END)
        assert caught.value.retry_after == 30

    async def test_html_body_with_200_is_unavailable(self):
        recorder = respond(200, text="<html>maintenance</html>")
        with pytest.raises(ProviderUnavailable):
            await self.provider(recorder).fetch_daily_closes("AAPL.US", START, END)


# ------------------------------------------------------------------- Twelve Data


class TestTwelveData:
    def provider(self, recorder):
        return TwelveDataProvider(api_key=SECRET, transport=recorder.transport)

    async def test_asks_one_more_day_because_end_date_is_exclusive(self):
        recorder = respond(
            body={
                "meta": {"symbol": "AAPL", "interval": "1day", "currency": "USD"},
                "values": [
                    {"datetime": "2026-11-12", "close": "354.88000"},
                    {"datetime": "2026-11-13", "close": "356.10000"},
                    {"datetime": "2026-11-14", "close": "999"},
                ],
                "status": "ok",
            }
        )
        closes = await self.provider(recorder).fetch_daily_closes("AAPL", START, END)
        assert recorder.last.url.params["end_date"] == "2026-11-14"
        assert recorder.last.url.params["start_date"] == "2026-11-02"
        assert [(c.price_date, c.close) for c in closes] == [
            (date(2026, 11, 12), Decimal("354.88000")),
            (date(2026, 11, 13), Decimal("356.10000")),
        ]

    async def test_unknown_symbol(self):
        recorder = respond(
            404,
            {
                "code": 404,
                "message": "**symbol** or **figi** parameter is missing or invalid.",
                "status": "error",
            },
        )
        with pytest.raises(SymbolNotSupported):
            await self.provider(recorder).fetch_daily_closes("ZZZQX", START, END)

    async def test_plan_does_not_cover_bmv(self):
        recorder = respond(
            200,
            {
                "code": 404,
                "message": "This symbol is available starting with the Pro plan.",
                "status": "error",
            },
        )
        with pytest.raises(SymbolNotSupported):
            await self.provider(recorder).fetch_daily_closes("WALMEX", START, END)

    async def test_no_data_on_dates_is_empty(self):
        recorder = respond(
            400,
            {
                "code": 400,
                "message": "No data is available on the specified dates. Try ...",
                "status": "error",
            },
        )
        closes = await self.provider(recorder).fetch_daily_closes(
            "AAPL", date(2026, 11, 7), date(2026, 11, 8)
        )
        assert closes == []

    async def test_invalid_key_is_unavailable(self):
        recorder = respond(
            401,
            {
                "code": 401,
                "message": "**apikey** parameter is incorrect or not specified.",
                "status": "error",
            },
        )
        with pytest.raises(ProviderUnavailable) as caught:
            await self.provider(recorder).fetch_daily_closes("AAPL", START, END)
        assert_no_secret(caught.value)

    async def test_minute_limit_in_body(self):
        recorder = respond(
            200,
            {
                "code": 429,
                "message": "You have run out of API credits for the current minute.",
                "status": "error",
            },
        )
        with pytest.raises(QuotaExhausted) as caught:
            await self.provider(recorder).fetch_daily_closes("AAPL", START, END)
        assert caught.value.retry_after == 60

    async def test_daily_limit_in_body(self, monkeypatch):
        import infrastructure.external_services.market_data.twelvedata as module

        monkeypatch.setattr(module, "seconds_until_utc_midnight", lambda: 5000)
        recorder = respond(
            200,
            {
                "code": 429,
                "message": "You have run out of API credits for the day.",
                "status": "error",
            },
        )
        with pytest.raises(QuotaExhausted) as caught:
            await self.provider(recorder).fetch_daily_closes("AAPL", START, END)
        assert caught.value.retry_after == 5000


# ----------------------------------------------------------------------- Banxico


def banxico_body(datos=None):
    serie = {"idSerie": "SF43718", "titulo": "Tipo de cambio ... (FIX)"}
    if datos is not None:
        serie["datos"] = datos
    return {"bmx": {"series": [serie]}}


class TestBanxico:
    def provider(self, recorder):
        return BanxicoFxProvider(token=SECRET, transport=recorder.transport)

    async def test_parses_fix(self):
        recorder = respond(
            body=banxico_body(
                [
                    {"fecha": "13/11/2026", "dato": "18.5525"},
                    {"fecha": "12/11/2026", "dato": "18.6188"},
                    {"fecha": "11/11/2026", "dato": "N/E"},
                    {"fecha": "10/11/2026", "dato": "1,018.50"},
                ]
            )
        )
        rates = await self.provider(recorder).fetch_rates("USD", "MXN", START, END)
        assert [(r.rate_date, r.rate) for r in rates] == [
            (date(2026, 11, 10), Decimal("1018.50")),
            (date(2026, 11, 12), Decimal("18.6188")),
            (date(2026, 11, 13), Decimal("18.5525")),
        ]
        assert recorder.last.url.path.endswith(
            "/series/SF43718/datos/2026-11-02/2026-11-13"
        )
        assert recorder.last.headers["Bmx-Token"] == SECRET

    async def test_range_without_data(self):
        recorder = respond(body=banxico_body())
        rates = await self.provider(recorder).fetch_rates(
            "usd", "mxn", date(2026, 11, 7), date(2026, 11, 8)
        )
        assert rates == []

    async def test_invalid_token(self):
        recorder = respond(
            400,
            {
                "error": {
                    "mensaje": "Token inválido",
                    "detalle": "El token enviado no es válido, favor de verificar.",
                }
            },
        )
        with pytest.raises(ProviderUnavailable, match="Token inválido") as caught:
            await self.provider(recorder).fetch_rates("USD", "MXN", START, END)
        assert_no_secret(caught.value)

    async def test_euro_uses_its_own_series(self):
        # Respuesta real de SF46410 («Euro respecto al peso mexicano»), 13/11/2026.
        recorder = respond(body=banxico_body([{"fecha": "13/11/2026", "dato": "20.5085"}]))
        rates = await self.provider(recorder).fetch_rates("EUR", "MXN", START, END)
        assert [(r.rate_date, r.rate) for r in rates] == [
            (date(2026, 11, 13), Decimal("20.5085"))
        ]
        assert recorder.last.url.path.endswith(
            "/series/SF46410/datos/2026-11-02/2026-11-13"
        )

    async def test_other_pairs_are_not_supported(self):
        provider = BanxicoFxProvider(token=SECRET)
        assert provider.supports("USD", "MXN") and provider.supports("eur", "mxn")
        assert not provider.supports("GBP", "MXN")
        with pytest.raises(SymbolNotSupported):
            await provider.fetch_rates("GBP", "MXN", START, END)


# ------------------------------------------------------------------------- Yahoo


def _ts(day: date, hour: int, minute: int) -> int:
    return int(
        datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC).timestamp()
    )


class TestYahoo:
    def provider(self, recorder):
        return YahooProvider(transport=recorder.transport)

    def test_symbol_translation(self):
        provider = YahooProvider()
        assert provider.provider_symbol(Market.BMV, "WALMEX*") == "WALMEX.MX"
        assert provider.provider_symbol(Market.US, "BRK.B") == "BRK-B"

    async def test_uses_exchange_local_date(self):
        # Apertura de la BMV 08:30 local = 14:30 UTC (gmtoffset -21600).
        body = {
            "chart": {
                "result": [
                    {
                        "meta": {"currency": "MXN", "gmtoffset": -21600},
                        "timestamp": [
                            _ts(date(2026, 11, 12), 14, 30),
                            _ts(date(2026, 11, 13), 14, 30),
                            _ts(date(2026, 11, 14), 1, 0),  # 13-nov 19:00 local
                        ],
                        "indicators": {
                            "quote": [{"close": [54.2400016784668, None, 54.79]}]
                        },
                    }
                ],
                "error": None,
            }
        }
        recorder = respond(body=body)
        closes = await self.provider(recorder).fetch_daily_closes(
            "WALMEX.MX", START, END
        )
        assert [(c.price_date, c.close) for c in closes] == [
            (date(2026, 11, 12), Decimal("54.240002")),
            (date(2026, 11, 13), Decimal("54.79")),
        ]
        assert "Mozilla" in recorder.last.headers["User-Agent"]

    async def test_unknown_symbol(self):
        recorder = respond(
            404,
            {
                "chart": {
                    "result": None,
                    "error": {"code": "Not Found", "description": "No data found"},
                }
            },
        )
        with pytest.raises(SymbolNotSupported):
            await self.provider(recorder).fetch_daily_closes("ZZZQX.MX", START, END)


def test_keys_are_required():
    with pytest.raises(ValueError):
        DataBursatilProvider(token="")
    with pytest.raises(ValueError):
        EodhdProvider(api_key="")
    with pytest.raises(ValueError):
        TwelveDataProvider(api_key="")
    with pytest.raises(ValueError):
        BanxicoFxProvider(token="")


def test_seconds_until_utc_midnight():
    now = datetime(2026, 11, 14, 23, 59, 30, tzinfo=UTC)
    assert seconds_until_utc_midnight(now) == 30


# ------------------------------------------------------------- catálogo y búsqueda


class TestDataBursatilCatalog:
    async def test_parses_issuers_and_series(self):
        recorder = respond(
            body={
                "None": {"None": {"razon_social": None, "estatus": "ACTIVA"}},
                "WALMEX": {
                    "*": {
                        "razon_social": "WAL - MART DE MEXICO, S.A.B. DE C.V.",
                        "isin": "MX01WA000038",
                        "bolsa": "BMV",
                        "tipo_valor_descripcion": "ACCIONES DE EMPRESAS COMERCIALES, INDUSTRIALES Y DE SERVICIOS",
                        "tipo_valor_id": "1",
                        "estatus": "ACTIVA",
                    }
                },
                "FUNO": {
                    "11": {
                        "razon_social": "BANCO ACTINVER",
                        "isin": "MXCFFU000001",
                        "bolsa": "BMV",
                        "tipo_valor_descripcion": "FIBRAS CERTIFICADOS INMOBILIARIOS",
                        "estatus": "ACTIVA",
                    }
                },
                "AA1CK": {
                    "17": {
                        "razon_social": "BANCO INVEX",
                        "isin": "bad",
                        "tipo_valor_descripcion": "CERTIFICADOS DE CAPITAL DE DESARROLLO",
                        "estatus": "SUSPENDIDA",
                    }
                },
            }
        )
        provider = DataBursatilProvider(token=SECRET, transport=recorder.transport)

        listings = {l.symbol: l for l in await provider.fetch_catalog(Market.BMV)}

        assert set(listings) == {"WALMEX*", "FUNO11", "AA1CK17"}
        assert listings["WALMEX*"].instrument_type is InstrumentType.STOCK
        assert listings["WALMEX*"].isin == "MX01WA000038"
        assert listings["WALMEX*"].exchange == "BMV"
        assert listings["FUNO11"].instrument_type is InstrumentType.FIBRA
        assert listings["AA1CK17"].instrument_type is InstrumentType.OTHER
        assert listings["AA1CK17"].is_active is False
        assert listings["AA1CK17"].isin is None
        assert recorder.last.url.params["mercado"] == "local"

    async def test_sic_is_the_global_segment(self):
        recorder = respond(
            body={
                "IVV": {
                    "*": {
                        "razon_social": "ISHARES CORE S&P 500 ETF",
                        "isin": "US4642872000",
                        "bolsa": "NEW YORK STOCK EXCHANGE",
                        "tipo_valor_descripcion": "CANASTA DE ACCIONES (TRAC'S EXTRANJEROS)",
                        "estatus": "ACTIVA",
                    }
                }
            }
        )
        provider = DataBursatilProvider(token=SECRET, transport=recorder.transport)
        [ivv] = await provider.fetch_catalog(Market.SIC)
        assert (ivv.market, ivv.symbol, ivv.instrument_type, ivv.currency) == (
            Market.SIC,
            "IVV*",
            InstrumentType.ETF,
            "MXN",
        )
        assert recorder.last.url.params["mercado"] == "global"

    async def test_no_catalog_for_us(self):
        provider = DataBursatilProvider(token=SECRET)
        with pytest.raises(SymbolNotSupported):
            await provider.fetch_catalog(Market.US)


class TestTwelveDataSearch:
    async def test_keeps_the_us_listing_once(self):
        recorder = respond(
            body={
                "data": [
                    {
                        "symbol": "AAPL",
                        "instrument_name": "Apple Inc.",
                        "exchange": "NASDAQ",
                        "instrument_type": "Common Stock",
                        "country": "United States",
                        "currency": "USD",
                    },
                    {
                        "symbol": "AAPL",
                        "instrument_name": "Apple Inc. CEDEAR",
                        "exchange": "BCBA",
                        "instrument_type": "Depositary Receipt",
                        "country": "Argentina",
                        "currency": "ARS",
                    },
                    {
                        "symbol": "AAPL",
                        "instrument_name": "Apple Inc.",
                        "exchange": "XETR",
                        "instrument_type": "Common Stock",
                        "country": "United States",
                        "currency": "USD",
                    },
                    {
                        "symbol": "AAPU",
                        "instrument_name": "Direxion Daily AAPL Bull 2X",
                        "exchange": "NASDAQ",
                        "instrument_type": "ETF",
                        "country": "United States",
                        "currency": "USD",
                    },
                ],
                "status": "ok",
            }
        )
        provider = TwelveDataProvider(api_key=SECRET, transport=recorder.transport)

        listings = await provider.search("aapl", Market.US)

        assert [(l.symbol, l.instrument_type, l.exchange) for l in listings] == [
            ("AAPL", InstrumentType.STOCK, "NASDAQ"),
            ("AAPU", InstrumentType.ETF, "NASDAQ"),
        ]
        assert recorder.last.url.params["symbol"] == "aapl"

    async def test_only_us(self):
        provider = TwelveDataProvider(api_key=SECRET)
        assert await provider.search("WALMEX", Market.BMV) == []
