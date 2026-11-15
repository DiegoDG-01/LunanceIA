"""Operaciones sobre valores y su tenencia con costo promedio."""

from datetime import date
from decimal import Decimal

import pytest

from domain.entities.securities.security_trade import SecurityTrade
from domain.objects.enums import HoldingStatus, TradeType
from domain.services.holding_ledger import replay
from shared.exceptions.domain import InsufficientSharesError, InvalidSecurityTradeError

D = Decimal
_ids = iter(range(1, 10_000))


def trade(kind: TradeType, day: int, *, persisted: bool = True, **fields) -> SecurityTrade:
    t = SecurityTrade.create(
        user_id=1,
        account_id=1,
        instrument_id=1,
        trade_type=kind,
        trade_date=date(2026, 11, day),
        **fields,
    )
    if persisted:
        t.id = next(_ids)
    return t


def buy(day, qty, price, fees="0"):
    return trade(TradeType.BUY, day, quantity=D(qty), price=D(price), fees=D(fees))


def sell(day, qty, price, fees="0", tax="0"):
    return trade(
        TradeType.SELL,
        day,
        quantity=D(qty),
        price=D(price),
        fees=D(fees),
        tax_withheld=D(tax),
    )


class TestTradeValidation:
    def test_buy_cash_includes_fees(self):
        t = buy(2, "10", "54.79", "11.60")
        assert t.cash_amount == D("559.50")

    def test_sell_cash_subtracts_fees_and_tax(self):
        t = sell(2, "10", "60", "11.60", "3.00")
        assert t.cash_amount == D("585.40")

    def test_cash_is_rounded_to_cents(self):
        t = buy(2, "0.333", "10.005")
        assert t.cash_amount == D("3.33")

    def test_dividend_net(self):
        t = trade(
            TradeType.DIVIDEND, 2, gross_amount=D("100.00"), tax_withheld=D("10.00")
        )
        assert (t.cash_amount, t.quantity) == (D("90.00"), D(0))

    def test_split_moves_no_money(self):
        t = trade(TradeType.SPLIT, 2, split_from=1, split_to=3)
        assert t.cash_amount == 0
        assert not t.moves_money

    @pytest.mark.parametrize(
        ("kind", "fields"),
        [
            (TradeType.BUY, {"price": D("10")}),
            (TradeType.BUY, {"quantity": D("1"), "price": D("0")}),
            (TradeType.BUY, {"quantity": D("1.000000001"), "price": D("10")}),
            (TradeType.BUY, {"quantity": D("1"), "price": D("1.0000001")}),
            (TradeType.BUY, {"quantity": D("1"), "price": D("10"), "tax_withheld": D("1")}),
            (TradeType.BUY, {"quantity": D("1"), "price": D("10"), "fees": D("-1")}),
            (TradeType.BUY, {"quantity": D("1"), "price": D("10"), "fees": D("0.001")}),
            (TradeType.SELL, {"quantity": D("1"), "price": D("10"), "fees": D("10")}),
            (TradeType.SELL, {"quantity": D("1"), "price": D("10"), "gross_amount": D("1")}),
            (TradeType.DIVIDEND, {}),
            (TradeType.DIVIDEND, {"gross_amount": D("10"), "tax_withheld": D("10")}),
            (TradeType.DIVIDEND, {"gross_amount": D("10"), "quantity": D("1")}),
            (TradeType.SPLIT, {"split_from": 2}),
            (TradeType.SPLIT, {"split_from": 2, "split_to": 2}),
            (TradeType.SPLIT, {"split_from": 1, "split_to": 2, "price": D("1")}),
        ],
    )
    def test_rejects_fields_that_do_not_fit_the_type(self, kind, fields):
        with pytest.raises(InvalidSecurityTradeError):
            trade(kind, 2, **fields)

    def test_notes_are_trimmed(self):
        t = trade(TradeType.SPLIT, 2, split_from=1, split_to=2, notes="  ")
        assert t.notes is None


class TestReplay:
    def test_average_cost_includes_buy_fees(self):
        state = replay([buy(2, "10", "50", "10"), buy(3, "10", "60", "10")])
        assert state.quantity == D("20")
        assert state.cost_basis == D("1120.00")
        assert state.avg_cost == D("56.000000")
        assert state.status is HoldingStatus.OPEN
        assert state.opened_at == date(2026, 11, 2)

    def test_sell_realizes_against_average_cost(self):
        state = replay(
            [buy(2, "10", "50", "10"), buy(3, "10", "60", "10"), sell(4, "5", "70", "5")]
        )
        # 5 × 70 − 5 − 5 × 56 = 65
        assert state.realized == D("65.00")
        assert state.quantity == D("15")
        assert state.cost_basis == D("840.00")
        assert state.avg_cost == D("56.000000")

    def test_selling_everything_closes_and_a_new_buy_reopens(self):
        state = replay([buy(2, "10", "50"), sell(3, "10", "40")])
        assert state.status is HoldingStatus.CLOSED
        assert (state.cost_basis, state.avg_cost) == (D("0.00"), D(0))
        assert state.realized == D("-100.00")
        assert state.closed_at == date(2026, 11, 3)

        state = replay([buy(2, "10", "50"), sell(3, "10", "40"), buy(5, "1", "45")])
        assert state.status is HoldingStatus.OPEN
        assert (state.opened_at, state.closed_at) == (date(2026, 11, 5), None)
        assert state.avg_cost == D("45.000000")

    def test_order_is_by_date_then_registration(self):
        # Registrada al final pero con fecha anterior: va primero.
        late = buy(2, "10", "50")
        state = replay([sell(3, "5", "60"), late])
        assert state.quantity == D("5")

    def test_unsaved_trade_goes_after_saved_ones_of_the_same_day(self):
        saved = buy(2, "10", "50")
        new = sell(2, "10", "55")
        new.id = None
        assert replay([new, saved]).quantity == 0

    def test_cannot_sell_more_than_held(self):
        with pytest.raises(InsufficientSharesError, match="WALMEX\\*"):
            replay([buy(2, "10", "50"), sell(3, "11", "50")], symbol="WALMEX*")

    def test_cannot_sell_before_buying(self):
        with pytest.raises(InsufficientSharesError):
            replay([sell(2, "1", "50"), buy(3, "10", "50")])

    def test_dividends_add_up_and_need_a_prior_buy(self):
        dividend = trade(TradeType.DIVIDEND, 4, gross_amount=D("12.50"))
        state = replay([buy(2, "10", "50"), dividend])
        assert state.dividends == D("12.50")
        with pytest.raises(InvalidSecurityTradeError):
            replay([dividend])

    def test_split_keeps_total_cost(self):
        split = trade(TradeType.SPLIT, 4, split_from=1, split_to=4)
        state = replay([buy(2, "10", "100", "8"), split])
        assert state.quantity == D("40")
        assert state.cost_basis == D("1008.00")
        assert state.avg_cost == D("25.200000")

    def test_reverse_split(self):
        split = trade(TradeType.SPLIT, 4, split_from=10, split_to=1)
        state = replay([buy(2, "100", "1"), split])
        assert state.quantity == D("10")
        assert state.avg_cost == D("10.000000")

    def test_split_needs_shares(self):
        with pytest.raises(InsufficientSharesError):
            replay([trade(TradeType.SPLIT, 2, split_from=1, split_to=2)])

    def test_fractional_shares(self):
        state = replay([buy(2, "0.5", "300.10"), sell(3, "0.25", "310")])
        assert state.quantity == D("0.25")
        assert state.cost_basis == D("75.03")  # 150.05 / 2, redondeado al final
