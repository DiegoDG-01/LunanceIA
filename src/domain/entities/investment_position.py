from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, cast

from domain.objects.enums import (
    InterestType,
    MaturityAction,
    PositionStatus,
    PositionType,
)
from domain.objects.money import Money
from shared.exceptions.domain import (
    FixedTermDepositNotAllowedError,
    FixedTermWithdrawalNotAllowedError,
    InvalidFixedTermConfigError,
    InvalidInvestmentRateError,
    InvalidPenaltyPercentageError,
    InvestmentPositionLockedError,
    InvestmentPositionNotActiveError,
    InvestmentPositionNotMaturedError,
)


@dataclass
class InvestmentPosition:
    """Apartado de inversión dentro de una cuenta.

    El dinero de un apartado NO forma parte del current_balance de la cuenta:
    para gastarlo o transferirlo primero debe regresarse al saldo disponible.
    """

    id: Optional[int]
    uuid: Optional[str]
    account_id: int
    name: str
    position_type: PositionType
    status: PositionStatus
    balance: Money  # Capital del apartado
    accrued_yield: Money  # Solo plazo fijo: rendimiento acumulado aún no entregado
    annual_rate: Decimal
    interest_type: InterestType
    start_date: date
    on_maturity: MaturityAction
    base_principal: Optional[Decimal] = None  # Base de cálculo para interés simple
    term_days: Optional[int] = None
    lock_period_end_date: Optional[date] = None
    maturity_date: Optional[date] = None
    early_withdrawal_penalty: Optional[Decimal] = None
    created_at: Optional[datetime] = None

    @classmethod
    def create_new(
        cls,
        account_id: int,
        name: str,
        position_type: PositionType,
        initial_balance: Money,
        annual_rate: Decimal,
        interest_type: InterestType = InterestType.COMPOUND,
        start_date: Optional[date] = None,
        term_days: Optional[int] = None,
        maturity_date: Optional[date] = None,
        lock_period_end_date: Optional[date] = None,
        early_withdrawal_penalty: Optional[Decimal] = None,
        on_maturity: MaturityAction = MaturityAction.HOLD,
    ) -> "InvestmentPosition":
        if annual_rate < 0:
            raise InvalidInvestmentRateError(str(annual_rate))
        if early_withdrawal_penalty is not None:
            if not 0 <= early_withdrawal_penalty <= 100:
                raise InvalidPenaltyPercentageError(str(early_withdrawal_penalty))

        if start_date is None:
            start_date = datetime.now(timezone.utc).date()

        if position_type == PositionType.FIXED_TERM:
            if maturity_date is None:
                if term_days is None:
                    raise InvalidFixedTermConfigError()
                maturity_date = start_date + timedelta(days=term_days)
            elif term_days is None:
                term_days = (maturity_date - start_date).days
            if term_days <= 0 or maturity_date <= start_date:
                raise InvalidFixedTermConfigError()
        else:
            term_days = None
            maturity_date = None
            lock_period_end_date = None
            early_withdrawal_penalty = None

        base_principal = None
        if interest_type == InterestType.SIMPLE:
            base_principal = initial_balance.amount

        return cls(
            id=None,
            uuid=None,
            account_id=account_id,
            name=name,
            position_type=position_type,
            status=PositionStatus.ACTIVE,
            balance=initial_balance,
            accrued_yield=Money(Decimal(0), initial_balance.currency),
            annual_rate=annual_rate,
            interest_type=interest_type,
            start_date=start_date,
            on_maturity=on_maturity,
            base_principal=base_principal,
            term_days=term_days,
            lock_period_end_date=lock_period_end_date,
            maturity_date=maturity_date,
            early_withdrawal_penalty=early_withdrawal_penalty,
            created_at=None,
        )

    @property
    def total_value(self) -> Money:
        """Capital + rendimiento acumulado aún no entregado."""
        return self.balance.add(self.accrued_yield)

    def _ensure_active(self) -> None:
        if self.status != PositionStatus.ACTIVE:
            raise InvestmentPositionNotActiveError(str(self.uuid), self.status.value)

    def accrue_yield(self, amount: Money) -> None:
        """Registra el rendimiento de un día: a la vista capitaliza en el
        balance; a plazo fijo se acumula aparte hasta el vencimiento."""
        self._ensure_active()
        if self.position_type == PositionType.ON_DEMAND:
            self.balance = self.balance.add(amount)
        else:
            self.accrued_yield = self.accrued_yield.add(amount)

    def deposit(self, amount: Money) -> None:
        self._ensure_active()
        if self.position_type == PositionType.FIXED_TERM:
            raise FixedTermDepositNotAllowedError(str(self.uuid))
        self.balance = self.balance.add(amount)
        if self.base_principal is not None:
            self.base_principal += amount.amount

    def withdraw(self, amount: Money) -> None:
        self._ensure_active()
        if self.position_type == PositionType.FIXED_TERM:
            raise FixedTermWithdrawalNotAllowedError(str(self.uuid))
        self.balance = self.balance.subtract(amount)
        if self.base_principal is not None:
            # El retiro consume primero rendimientos capitalizados; el capital
            # base solo baja si el balance cae por debajo de él.
            self.base_principal = min(self.base_principal, self.balance.amount)

    def is_due_for_maturity(self, as_of: date) -> bool:
        return (
            self.position_type == PositionType.FIXED_TERM
            and self.status == PositionStatus.ACTIVE
            and self.maturity_date is not None
            and as_of >= self.maturity_date
        )

    def mark_matured(self) -> None:
        """Deja el apartado en espera de acción del usuario (on_maturity=HOLD).
        En estado MATURED el apartado deja de generar rendimiento."""
        self._ensure_active()
        self.status = PositionStatus.MATURED

    def renew(self, as_of: date) -> None:
        """Reinvierte capital + rendimiento por el mismo plazo (AUTO_RENEW)."""
        if self.status == PositionStatus.LIQUIDATED:
            raise InvestmentPositionNotActiveError(str(self.uuid), self.status.value)
        if self.maturity_date is None or as_of < self.maturity_date:
            raise InvestmentPositionNotMaturedError(
                str(self.uuid), str(self.maturity_date)
            )
        self.balance = self.balance.add(self.accrued_yield)
        self.accrued_yield = Money(Decimal(0), self.balance.currency)
        if self.interest_type == InterestType.SIMPLE:
            self.base_principal = self.balance.amount
        self.start_date = as_of
        self.maturity_date = as_of + timedelta(days=cast(int, self.term_days))
        # El periodo de permanencia solo aplica al primer ciclo
        self.lock_period_end_date = None
        self.status = PositionStatus.ACTIVE

    def liquidate(self, as_of: date) -> Money:
        """Cierra el apartado y devuelve el monto a regresar al disponible.

        Liquidar un plazo fijo antes del vencimiento aplica la penalización
        sobre el rendimiento acumulado (nunca sobre el capital); antes del fin
        del periodo de permanencia no se permite liquidar.
        """
        if self.status == PositionStatus.LIQUIDATED:
            raise InvestmentPositionNotActiveError(str(self.uuid), self.status.value)

        payout = self.balance.add(self.accrued_yield)

        is_early = (
            self.position_type == PositionType.FIXED_TERM
            and self.status == PositionStatus.ACTIVE
            and self.maturity_date is not None
            and as_of < self.maturity_date
        )
        if is_early:
            if self.lock_period_end_date and as_of < self.lock_period_end_date:
                raise InvestmentPositionLockedError(
                    str(self.uuid), str(self.lock_period_end_date)
                )
            penalty = self.early_withdrawal_penalty or Decimal(0)
            kept_yield = (
                self.accrued_yield.amount * (1 - penalty / Decimal(100))
            ).quantize(Decimal("0.01"))
            payout = self.balance.add(Money(kept_yield, self.balance.currency))

        self.balance = Money(Decimal(0), self.balance.currency)
        self.accrued_yield = Money(Decimal(0), self.balance.currency)
        self.status = PositionStatus.LIQUIDATED
        return payout
