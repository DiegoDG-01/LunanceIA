"""Fotos diarias de una tenencia."""

from datetime import date
from decimal import Decimal

from domain.entities.securities.security_trade import SecurityTrade
from domain.objects.enums import TradeType
from domain.services.holding_snapshots import daily_snapshots

D = Decimal
_ids = iter(range(1, 10_000))


def nov(day: int) -> date:
    return date(2026, 11, day)


def trade(kind, day, **fields):
    t = SecurityTrade.create(
        user_id=1,
        account_id=1,
        instrument_id=1,
        trade_type=kind,
        trade_date=nov(day),
        **fields,
    )
    t.id = next(_ids)
    return t


def by_day(snapshots):
    return {s.snapshot_date.day: s for s in snapshots}


def test_one_snapshot_per_calendar_day_carrying_the_last_close():
    trades = [trade(TradeType.BUY, 5, quantity=D("10"), price=D("50"), fees=D("10"))]
    closes = [(nov(5), D("51")), (nov(6), D("52")), (nov(9), D("53"))]

    days = by_day(
        daily_snapshots(
            holding_id=7, trades=trades, start=nov(5), end=nov(10), closes=closes
        )
    )

    assert sorted(days) == [5, 6, 7, 8, 9, 10]
    assert days[5].market_value == D("510.00")
    assert days[5].unrealized_pnl == D("0.00")  # costo 510 con la comisión
    # Sábado y domingo: el cierre del viernes.
    assert (days[7].close, days[7].price_date) == (D("52"), nov(6))
    assert days[8].market_value == D("520.00")
    assert days[10].price_date == nov(9)
    assert days[10].market_value_mxn == days[10].market_value
    assert days[10].fx_rate is None
    assert all(s.holding_id == 7 for s in days.values())


def test_no_valuation_before_the_first_close():
    trades = [trade(TradeType.BUY, 2, quantity=D("1"), price=D("50"))]
    days = by_day(
        daily_snapshots(
            holding_id=1, trades=trades, start=nov(2), end=nov(4), closes=[(nov(4), D("55"))]
        )
    )
    assert days[2].market_value is None and days[2].cost_basis == D("50.00")
    assert days[4].market_value == D("55.00")


def test_trades_count_on_their_day_and_earlier_ones_are_replayed():
    trades = [
        trade(TradeType.BUY, 2, quantity=D("10"), price=D("50")),
        trade(TradeType.SELL, 6, quantity=D("4"), price=D("60")),
        trade(TradeType.DIVIDEND, 8, gross_amount=D("5.00")),
        trade(TradeType.SPLIT, 9, split_from=1, split_to=2),
    ]
    # Empieza a mitad: las operaciones anteriores al rango arman el estado inicial.
    days = by_day(
        daily_snapshots(
            holding_id=1,
            trades=trades,
            start=nov(5),
            end=nov(9),
            closes=[(nov(3), D("55"))],
        )
    )
    assert days[5].quantity == D("10")
    assert days[5].close == D("55")  # arrastrado desde antes del rango
    assert days[6].quantity == D("6")
    assert days[6].realized_pnl == D("40.00")
    assert days[7].dividends == D("0.00")
    assert days[8].dividends == D("5.00")
    assert days[9].quantity == D("12")
    assert days[9].cost_basis == D("300.00")


def test_dollar_values_use_the_fx_of_the_day_or_the_last_one():
    trades = [trade(TradeType.BUY, 5, quantity=D("2"), price=D("200"))]
    days = by_day(
        daily_snapshots(
            holding_id=1,
            trades=trades,
            start=nov(5),
            end=nov(9),
            closes=[(nov(5), D("210"))],
            fx_rates=[(nov(4), D("18.5")), (nov(6), D("18.6"))],
        )
    )
    assert (days[5].fx_rate, days[5].market_value_mxn) == (D("18.5"), D("7770.00"))
    assert days[9].fx_rate == D("18.6")
    assert days[9].market_value_mxn == D("7812.00")


def test_dollar_values_without_fx_have_no_peso_value():
    trades = [trade(TradeType.BUY, 5, quantity=D("2"), price=D("200"))]
    [day] = daily_snapshots(
        holding_id=1,
        trades=trades,
        start=nov(5),
        end=nov(5),
        closes=[(nov(5), D("210"))],
        fx_rates=[],
    )
    assert day.market_value == D("420.00")
    assert day.market_value_mxn is None
