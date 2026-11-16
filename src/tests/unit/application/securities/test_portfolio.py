"""Patrimonio e historia de lo invertido, con repositorios reales sobre SQLite."""

from datetime import date

from application.securities.queries.portfolio import PortfolioQueries
from domain.entities.securities.exchange_rate import ExchangeRate
from domain.objects.enums import (
    AccountType,
    InterestType,
    Market,
    PositionStatus,
    PositionType,
    TradeType,
)
from infrastructure.database.models import InvestmentPositionModel, InvestmentYieldModel
from infrastructure.database.repositories.sqlalchemy_currency_demand_repository import (
    SQLAlchemyCurrencyDemandRepository,
)
from infrastructure.database.repositories.sqlalchemy_portfolio_repository import (
    SQLAlchemyPortfolioReadRepository,
)

from .test_snapshots import nov, price, rebuild
from .test_trades import (  # noqa: F401 - fixtures
    TODAY,
    USER_ID,
    D,
    account,
    env,
    make_account,
    make_instrument,
    walmex,
)


def portfolio(env) -> PortfolioQueries:
    return PortfolioQueries(
        read_repository=SQLAlchemyPortfolioReadRepository(env.db),
        fx_repository=env.fx,
        holding_queries=env.queries(),
        today=lambda: TODAY,
    )


async def make_position(
    env,
    account,
    *,
    balance="1000",
    accrued="0",
    currency="MXN",
    status=PositionStatus.ACTIVE,
    yields: dict[date, str] | None = None,
) -> int:
    position = InvestmentPositionModel(
        account_id=account.id,
        name="Apartado",
        position_type=PositionType.ON_DEMAND,
        status=status,
        balance=D(balance),
        accrued_yield=D(accrued),
        currency=currency,
        annual_rate=D("10"),
        interest_type=InterestType.COMPOUND,
        start_date=date(2026, 10, 1),
    )
    env.db.add(position)
    await env.db.flush()
    for day, value in (yields or {}).items():
        env.db.add(
            InvestmentYieldModel(
                account_id=account.id,
                position_id=position.id,
                yield_date=day,
                principal_amount=D(value),
                yield_amount=D("0.10"),
                cumulative_balance=D(value),
                annual_rate=D("10"),
                interest_type=InterestType.COMPOUND,
            )
        )
    await env.db.flush()
    return position.id


async def fx(env, rates: dict[date, str], base="USD"):
    await env.fx.save_many(
        [
            ExchangeRate(
                base=base, quote="MXN", rate_date=d, rate=D(r), provider="banxico"
            )
            for d, r in rates.items()
        ]
    )


async def history(env, start: date, end: date):
    return {d.day: d for d in await portfolio(env).history(USER_ID, start, end)}


class TestSummary:
    async def test_adds_accounts_positions_and_holdings_in_pesos(
        self, env, account, walmex
    ):
        await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        await price(env, walmex, 13, "56")
        await make_account(env, balance="-1200", kind=AccountType.CREDIT_CARD)
        dollars = await make_account(env, balance="300", currency="USD")
        aapl = await make_instrument(env, "AAPL", Market.US, "USD")
        await env.record(dollars, aapl, day=3, quantity=D("1"), price=D("100"))
        await make_account(env, balance="50", currency="EUR")
        await fx(env, {nov(13): "18.5"})
        await make_position(env, account, balance="1000", accrued="25")
        await make_position(env, account, balance="0", status=PositionStatus.LIQUIDATED)

        summary = await portfolio(env).summary(USER_ID)

        # 10,000 − 500 de la compra, más 200 USD × 18.5.
        assert summary.cash == D("13200.00")
        assert summary.credit_cards == D("-1200.00")
        assert summary.positions == D("1025.00")
        assert summary.securities == D("560.00")
        assert summary.invested == D("1585.00")
        assert summary.net_worth == D("13585.00")
        assert summary.fx_rates == {"USD": D("18.50000000")}
        assert set(summary.missing) == {
            "Cuenta: sin tipo de cambio EUR/MXN",
            "AAPL: sin precio guardado",
        }

    async def test_empty_user(self, env):
        summary = await portfolio(env).summary(USER_ID)
        assert summary.net_worth == 0 and summary.missing == []


class TestPositionsHistory:
    async def test_carries_values_between_yields(self, env, account):
        await make_position(
            env,
            account,
            yields={date(2026, 10, 30): "1000", nov(2): "1001", nov(4): "1003"},
        )
        await make_position(
            env,
            account,
            status=PositionStatus.LIQUIDATED,
            yields={nov(2): "500", nov(3): "500.10"},
        )
        dollars = await make_account(env, currency="USD")
        await make_position(env, dollars, currency="USD", yields={nov(3): "10"})
        await fx(env, {date(2026, 10, 31): "18", nov(4): "19"})

        days = await history(env, nov(1), nov(5))

        assert {d.day: d.positions for d in days.values()} == {
            nov(1): D("1000.00"),  # el valor del 30 de octubre
            nov(2): D("1501.00"),
            nov(3): D("1681.10"),  # 1001 + 500.10 + 10 USD × 18
            nov(4): D("1193.00"),  # el liquidado ya no cuenta; 10 USD × 19
            nov(5): D("1193.00"),
        }
        assert all(d.complete and d.securities == 0 for d in days.values())

    async def test_skips_days_before_the_first_investment(self, env, account):
        await make_position(env, account, yields={date(2026, 10, 30): "1000"})
        days = await portfolio(env).history(USER_ID, date(2026, 10, 25), nov(1))
        assert [d.day for d in days] == [date(2026, 10, 30), date(2026, 10, 31), nov(1)]

    async def test_foreign_position_without_fx_is_incomplete(self, env):
        dollars = await make_account(env, currency="USD")
        await make_position(env, dollars, currency="USD", yields={nov(3): "10"})
        [day] = await portfolio(env).history(USER_ID, nov(3), nov(3))
        assert (day.positions, day.complete) == (D("0.00"), False)


class TestSecuritiesHistory:
    async def test_sums_snapshots_and_flags_days_not_built_yet(
        self, env, account, walmex
    ):
        await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        await price(env, walmex, 3, "51")
        await make_position(env, account, yields={nov(3): "1000"})
        await rebuild(env, 9)

        days = await history(env, nov(1), nov(11))

        assert min(days) == nov(3)
        assert days[nov(3)].securities == D("510.00")
        assert days[nov(3)].total == D("1510.00")
        assert days[nov(9)].complete
        # El job todavía no corre para el 10 y el 11.
        assert not days[nov(10)].complete and days[nov(10)].securities == 0

    async def test_days_without_a_close_or_waiting_for_a_rebuild(
        self, env, account, walmex
    ):
        bought = await env.record(
            account, walmex, day=3, quantity=D("10"), price=D("50")
        )
        await price(env, walmex, 5, "51")
        await rebuild(env, 9)

        days = await history(env, nov(3), nov(9))
        assert [d.complete for d in days.values()] == [False, False] + [True] * 5

        # Una edición marca la tenencia: sus días quedan pendientes hasta el job.
        await env.update(bought.trade.uuid, day=6, quantity=D("10"), price=D("50"))
        days = await history(env, nov(3), nov(9))
        assert not any(d.complete for d in days.values())

        await rebuild(env, 9)
        days = await history(env, nov(3), nov(9))
        assert min(days) == nov(6)
        assert all(d.complete for d in days.values())

    async def test_closed_holding_does_not_hold_back_later_days(
        self, env, account, walmex
    ):
        await env.record(account, walmex, day=3, quantity=D("10"), price=D("50"))
        await env.record(
            account, walmex, TradeType.SELL, day=5, quantity=D("10"), price=D("55")
        )
        await price(env, walmex, 3, "51")
        await make_position(env, account, yields={nov(3): "1000"})
        await rebuild(env, 9)

        days = await history(env, nov(3), nov(9))
        assert days[nov(5)].securities == 0  # sin títulos al cierre del día
        assert all(d.complete for d in days.values())


class TestEuro:
    async def test_summary_converts_euro_accounts(self, env, account):
        await make_account(env, balance="100", currency="EUR")
        await fx(env, {nov(13): "20.5"}, base="EUR")

        summary = await portfolio(env).summary(USER_ID)

        assert summary.fx_rates == {"EUR": D("20.50000000")}
        assert summary.missing == []
        assert summary.cash == D("12050.00")  # 10,000 + 100 EUR × 20.5

    async def test_history_converts_euro_positions(self, env):
        euros = await make_account(env, currency="EUR")
        await make_position(env, euros, currency="EUR", yields={nov(3): "10"})
        await fx(env, {nov(2): "20", nov(4): "21"}, base="EUR")

        days = await history(env, nov(3), nov(4))

        assert [days[nov(3)].positions, days[nov(4)].positions] == [D("200.00"), D("210.00")]
        assert all(d.complete for d in days.values())


class TestCurrencyDemand:
    async def test_accounts_and_positions_outside_pesos(self, env, account):
        await make_account(env, currency="USD")
        euros = await make_account(env, currency="EUR")
        await make_position(env, euros, currency="EUR")

        demand = await SQLAlchemyCurrencyDemandRepository(env.db).since()

        # Cuentas en USD: solo días recientes. EUR: desde que empezó el apartado.
        assert demand == {"USD": None, "EUR": date(2026, 10, 1)}
