"""Lo invertido y el patrimonio del usuario, en pesos.

- Resumen (hoy): saldos de las cuentas, apartados y tenencias valuadas al último cierre.
- Historia: por día, apartados (su `cumulative_balance`, arrastrado entre rendimientos) más
  acciones (la suma de `market_value_mxn` de las fotos). Las cuentas no tienen histórico de
  saldo, así que la historia cubre solo lo invertido.

Lo que no tiene precio o tipo de cambio no se suma: el resumen dice qué faltó en `missing`
y la historia marca el día con `complete=False`.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from application.securities.portfolio_repository import (
    PortfolioReadRepository,
    PositionSeries,
)
from application.securities.queries.list_holdings import (
    HoldingQueries,
    ListHoldingsQuery,
)
from domain.objects.enums import AccountType, PositionStatus
from domain.repositories.securities.price_repository import ExchangeRateRepository

BASE_CURRENCY = "MXN"
CENT = Decimal("0.01")
ZERO = Decimal(0)


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    as_of: date
    # Disponible de las cuentas que no son tarjeta de crédito.
    cash: Decimal
    # Saldo de las tarjetas de crédito: negativo cuando hay deuda.
    credit_cards: Decimal
    positions: Decimal
    securities: Decimal
    invested: Decimal
    net_worth: Decimal
    # Tipos de cambio usados (pesos por unidad).
    fx_rates: dict[str, Decimal] = field(default_factory=dict)
    # Lo que no se pudo sumar y por qué.
    missing: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PortfolioDay:
    day: date
    positions: Decimal
    securities: Decimal
    total: Decimal
    complete: bool


class _Carry:
    """El último valor conocido a cada día, para días pedidos en orden creciente."""

    def __init__(self, points: list[tuple[date, Decimal]]) -> None:
        self._points = points
        self._next = 0
        self._value: Decimal | None = None

    def at(self, day: date) -> Decimal | None:
        while self._next < len(self._points) and self._points[self._next][0] <= day:
            self._value = self._points[self._next][1]
            self._next += 1
        return self._value


async def _rate_series(
    fx: ExchangeRateRepository, currency: str, start: date, end: date
) -> list[tuple[date, Decimal]]:
    """Tipos de cambio del rango más el último publicado antes de `start`."""
    seed = await fx.latest_on_or_before(
        currency, BASE_CURRENCY, start - timedelta(days=1)
    )
    rates = await fx.get_range(currency, BASE_CURRENCY, start, end)
    return ([(seed.rate_date, seed.rate)] if seed else []) + [
        (r.rate_date, r.rate) for r in rates
    ]


class _Position:
    """Valor diario de un apartado: el último `cumulative_balance` conocido.

    Antes del primer rendimiento vale 0; un apartado liquidado deja de contar después de
    su último rendimiento.
    """

    def __init__(self, series: PositionSeries) -> None:
        self.currency = series.currency
        self._closed_after = (
            series.last_yield_date
            if series.status is PositionStatus.LIQUIDATED
            else None
        )
        self._values = _Carry(series.points)

    def at(self, day: date) -> Decimal:
        value = self._values.at(day)
        if value is None or (self._closed_after and day > self._closed_after):
            return ZERO
        return value


class PortfolioQueries:
    def __init__(
        self,
        *,
        read_repository: PortfolioReadRepository,
        fx_repository: ExchangeRateRepository,
        holding_queries: HoldingQueries,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self._read = read_repository
        self._fx = fx_repository
        self._holdings = holding_queries
        self._today = today

    async def summary(self, user_id: int) -> PortfolioSummary:
        today = self._today()
        missing: list[str] = []
        rates: dict[str, Decimal | None] = {BASE_CURRENCY: Decimal(1)}

        async def to_mxn(amount: Decimal, currency: str, what: str) -> Decimal:
            if currency not in rates:
                rate = await self._fx.latest_on_or_before(
                    currency, BASE_CURRENCY, today
                )
                rates[currency] = rate.rate if rate else None
            rate = rates[currency]
            if rate is None:
                missing.append(f"{what}: sin tipo de cambio {currency}/{BASE_CURRENCY}")
                return ZERO
            return amount * rate

        cash = credit_cards = ZERO
        for account in await self._read.account_balances(user_id):
            value = await to_mxn(account.balance, account.currency, "Cuenta")
            if account.account_type is AccountType.CREDIT_CARD:
                credit_cards += value
            else:
                cash += value

        positions = ZERO
        for position in await self._read.position_balances(user_id):
            positions += await to_mxn(
                position.total_value, position.currency, "Apartado"
            )

        securities = ZERO
        for holding in await self._holdings.list_holdings(
            ListHoldingsQuery(user_id=user_id)
        ):
            symbol = holding.instrument.symbol
            if holding.market_value is None:
                missing.append(f"{symbol}: sin precio guardado")
            elif holding.market_value_mxn is None:
                missing.append(
                    f"{symbol}: sin tipo de cambio "
                    f"{holding.instrument.currency}/{BASE_CURRENCY}"
                )
            else:
                securities += holding.market_value_mxn
            if holding.fx_rate is not None:
                rates.setdefault(holding.instrument.currency, holding.fx_rate)

        cash, credit_cards = _money(cash), _money(credit_cards)
        positions, securities = _money(positions), _money(securities)
        invested = positions + securities
        return PortfolioSummary(
            as_of=today,
            cash=cash,
            credit_cards=credit_cards,
            positions=positions,
            securities=securities,
            invested=invested,
            net_worth=cash + credit_cards + invested,
            fx_rates={
                c: r for c, r in rates.items() if c != BASE_CURRENCY and r is not None
            },
            missing=missing,
        )

    async def history(self, user_id: int, start: date, end: date) -> list[PortfolioDay]:
        """Un punto por día de calendario. Los días anteriores a la primera inversión no
        se devuelven."""
        positions_series = [
            _Position(s) for s in await self._read.position_series(user_id, start, end)
        ]
        rates = {BASE_CURRENCY: _Carry([(start, Decimal(1))])}
        for currency in {p.currency for p in positions_series} - {BASE_CURRENCY}:
            rates[currency] = _Carry(await _rate_series(self._fx, currency, start, end))
        snapshots = {
            t.day: t for t in await self._read.snapshot_totals(user_id, start, end)
        }
        coverage = await self._read.holding_coverage(user_id)

        days: list[PortfolioDay] = []
        day = start
        while day <= end:
            complete = True
            positions = ZERO
            for position in positions_series:
                value = position.at(day)
                # Se pregunta siempre para que el cursor del tipo de cambio avance.
                rate = rates[position.currency].at(day)
                if value.is_zero():
                    continue
                if rate is None:
                    complete = False
                    continue
                positions += value * rate

            total = snapshots.get(day)
            securities = total.value_mxn if total else ZERO
            if (total and total.unvalued) or not all(c.covers(day) for c in coverage):
                complete = False

            positions, securities = _money(positions), _money(securities)
            if days or complete is False or not (positions + securities).is_zero():
                days.append(
                    PortfolioDay(
                        day=day,
                        positions=positions,
                        securities=securities,
                        total=positions + securities,
                        complete=complete,
                    )
                )
            day += timedelta(days=1)
        return days
