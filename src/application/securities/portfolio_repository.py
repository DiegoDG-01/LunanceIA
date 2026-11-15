"""Lecturas agregadas del portafolio: saldos, apartados y fotos de tenencias de un usuario.

Es un modelo de lectura (como el del dashboard): junta tablas de varios agregados sin
pasar por sus entidades, porque solo suma.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from domain.objects.enums import AccountType, PositionStatus


@dataclass(frozen=True, slots=True)
class AccountBalance:
    account_type: AccountType
    currency: str
    balance: Decimal


@dataclass(frozen=True, slots=True)
class PositionBalance:
    currency: str
    # Capital más rendimiento acumulado: lo que vale hoy el apartado.
    total_value: Decimal


@dataclass(frozen=True, slots=True)
class PositionSeries:
    """Valor diario de un apartado según sus rendimientos (`cumulative_balance`).

    `points` trae los rendimientos del rango y, si lo hay, el último anterior al rango
    para arrastrar su valor desde el primer día.
    """

    position_id: int
    currency: str
    status: PositionStatus
    # Último rendimiento registrado en toda su vida (puede quedar después del rango).
    last_yield_date: date
    points: list[tuple[date, Decimal]]


@dataclass(frozen=True, slots=True)
class SnapshotDayTotal:
    day: date
    value_mxn: Decimal
    # Fotos de ese día sin valor en pesos (sin cierre o sin tipo de cambio).
    unvalued: int


@dataclass(frozen=True, slots=True)
class HoldingCoverage:
    """Hasta dónde están al día las fotos de una tenencia."""

    opened_at: date | None
    closed_at: date | None
    snapshots_through: date | None
    snapshots_dirty_from: date | None

    def covers(self, day: date) -> bool:
        """False si la tenencia debería tener foto ese día y falta, o si se va a rehacer.

        La marca va primero: una operación movida a una fecha posterior deja fotos viejas
        antes de la nueva apertura hasta que el job las borra.
        """
        if self.snapshots_dirty_from is not None and day >= self.snapshots_dirty_from:
            return False
        if self.opened_at is None or day < self.opened_at:
            return True
        if self.closed_at is not None and day > self.closed_at:
            return True
        return self.snapshots_through is not None and day <= self.snapshots_through


class PortfolioReadRepository(ABC):
    @abstractmethod
    async def account_balances(self, user_id: int) -> list[AccountBalance]:
        """Saldo disponible de cada cuenta del usuario (las tarjetas de crédito, en
        negativo cuando hay deuda)."""

    @abstractmethod
    async def position_balances(self, user_id: int) -> list[PositionBalance]:
        """Apartados que no se han liquidado."""

    @abstractmethod
    async def position_series(
        self, user_id: int, start: date, end: date
    ) -> list[PositionSeries]:
        """Apartados con rendimientos en el rango o antes de él."""

    @abstractmethod
    async def snapshot_totals(
        self, user_id: int, start: date, end: date
    ) -> list[SnapshotDayTotal]:
        """Suma diaria de `market_value_mxn` de todas las tenencias del usuario."""

    @abstractmethod
    async def holding_coverage(self, user_id: int) -> list[HoldingCoverage]: ...
