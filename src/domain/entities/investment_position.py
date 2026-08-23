from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, cast

from domain.objects.enums import (
    InterestType,
    MaturityAction,
    OverflowAction,
    PositionStatus,
    PositionType,
)
from domain.objects.money import Money
from shared.exceptions.domain import (
    FixedTermCapNotAllowedError,
    FixedTermDepositNotAllowedError,
    FixedTermWithdrawalNotAllowedError,
    InvalidFixedTermConfigError,
    InvalidInvestmentRateError,
    InvalidOverflowTargetError,
    InvalidPenaltyPercentageError,
    InvalidPositionCapError,
    InvestmentPositionLockedError,
    InvestmentPositionNotActiveError,
    InvestmentPositionNotMaturedError,
    PositionCapExceededError,
)


@dataclass
class InvestmentPosition:
    """Apartado de inversión dentro de una cuenta.

    El dinero de un apartado NO forma parte del current_balance de la cuenta:
    para gastarlo o transferirlo primero debe regresarse al saldo disponible.

    Un apartado a la vista puede tener un tope (`max_balance`): el dinero que
    ya no cabe se desborda hacia el saldo disponible o hacia otro apartado.
    Encadenar apartados con topes distintos es como se representan las tasas
    por tramo de las SOFIPOs (25,000 al 10% y el excedente a otra tasa).
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
    max_balance: Optional[Decimal] = None  # Solo a la vista; None = sin tope
    overflow_action: Optional[OverflowAction] = None
    overflow_position_id: Optional[int] = None
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
        max_balance: Optional[Decimal] = None,
        overflow_action: Optional[OverflowAction] = None,
        overflow_position_id: Optional[int] = None,
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

        max_balance, overflow_action, overflow_position_id = cls._normalize_cap_config(
            position_type=position_type,
            max_balance=max_balance,
            overflow_action=overflow_action,
            overflow_position_id=overflow_position_id,
        )
        # Crear por encima del propio tope es un error de configuración, no algo
        # que desbordar: el usuario todavía puede corregir el monto o el tope.
        if max_balance is not None and initial_balance.amount > max_balance:
            raise PositionCapExceededError(
                str(initial_balance.amount), str(max_balance)
            )

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
            max_balance=max_balance,
            overflow_action=overflow_action,
            overflow_position_id=overflow_position_id,
            created_at=None,
        )

    @staticmethod
    def _normalize_cap_config(
        position_type: PositionType,
        max_balance: Optional[Decimal],
        overflow_action: Optional[OverflowAction],
        overflow_position_id: Optional[int],
        position_id: Optional[int] = None,
    ) -> tuple[Optional[Decimal], Optional[OverflowAction], Optional[int]]:
        """Valida la configuración de tope y devuelve los tres campos ya
        consistentes entre sí.

        Solo revisa la forma de la configuración. Que el apartado destino
        exista, sea de la misma cuenta y no cierre un ciclo se valida en la
        capa de aplicación, que sí puede consultarlo.
        """
        has_config = (
            max_balance is not None
            or overflow_action is not None
            or overflow_position_id is not None
        )

        if position_type == PositionType.FIXED_TERM:
            if has_config:
                raise FixedTermCapNotAllowedError()
            return None, None, None

        if max_balance is None:
            if has_config:
                raise InvalidPositionCapError(
                    "el destino de desbordamiento requiere un tope"
                )
            return None, None, None

        if max_balance <= 0:
            raise InvalidPositionCapError("el tope debe ser mayor a cero")

        # Un tope sin destino explícito devuelve el excedente al disponible:
        # es la única salida que nunca depende de otro apartado.
        action = overflow_action or OverflowAction.TO_AVAILABLE

        if action == OverflowAction.TO_POSITION:
            if overflow_position_id is None:
                raise InvalidOverflowTargetError(
                    "desbordar a un apartado requiere indicar cuál"
                )
            if position_id is not None and overflow_position_id == position_id:
                raise InvalidOverflowTargetError(
                    "un apartado no puede desbordarse a sí mismo"
                )
            return max_balance, action, overflow_position_id

        if overflow_position_id is not None:
            raise InvalidOverflowTargetError(
                f"{action.value} no admite un apartado destino"
            )
        return max_balance, action, None

    @property
    def total_value(self) -> Money:
        """Capital + rendimiento acumulado aún no entregado."""
        return self.balance.add(self.accrued_yield)

    def _zero(self) -> Money:
        return Money(Decimal(0), self.balance.currency)

    def _split_at_cap(self, amount: Money) -> tuple[Money, Money]:
        """Parte un monto entrante en lo que cabe bajo el tope y lo que sobra."""
        if self.max_balance is None:
            return amount, self._zero()

        room = self.max_balance - self.balance.amount
        if room <= 0:
            return self._zero(), amount
        if amount.amount <= room:
            return amount, self._zero()
        return (
            Money(room, amount.currency),
            Money(amount.amount - room, amount.currency),
        )

    def can_absorb(self) -> bool:
        """¿Puede recibir dinero de un desbordamiento?

        No mira el tope: un apartado lleno sigue siendo un destino válido y
        simplemente devuelve todo el monto como excedente para que la cadena
        continúe.
        """
        return (
            self.position_type == PositionType.ON_DEMAND
            and self.status == PositionStatus.ACTIVE
        )

    def _ensure_active(self) -> None:
        if self.status != PositionStatus.ACTIVE:
            raise InvestmentPositionNotActiveError(str(self.uuid), self.status.value)

    def accrue_yield(self, amount: Money) -> Money:
        """Registra el rendimiento de un día: a la vista capitaliza en el
        balance; a plazo fijo se acumula aparte hasta el vencimiento.

        Devuelve la parte del rendimiento que no cupo bajo el tope. Un
        apartado a la vista que ya está en su tope desborda el rendimiento
        completo todos los días: el tope no se rebasa ni un día.
        """
        self._ensure_active()
        if self.position_type != PositionType.ON_DEMAND:
            self.accrued_yield = self.accrued_yield.add(amount)
            return self._zero()

        accepted, overflow = self._split_at_cap(amount)
        self.balance = self.balance.add(accepted)
        return overflow

    def deposit(self, amount: Money) -> Money:
        """Abona al apartado y devuelve lo que no cupo bajo el tope."""
        self._ensure_active()
        if self.position_type == PositionType.FIXED_TERM:
            raise FixedTermDepositNotAllowedError(str(self.uuid))

        accepted, overflow = self._split_at_cap(amount)
        self.balance = self.balance.add(accepted)
        if self.base_principal is not None:
            # Solo el capital que entró mueve la base de cálculo del interés
            # simple; lo que se desborda nunca fue parte de este apartado.
            self.base_principal += accepted.amount
        return overflow

    def withdraw(self, amount: Money) -> None:
        self._ensure_active()
        if self.position_type == PositionType.FIXED_TERM:
            raise FixedTermWithdrawalNotAllowedError(str(self.uuid))
        self.balance = self.balance.subtract(amount)
        if self.base_principal is not None:
            # El retiro consume primero rendimientos capitalizados; el capital
            # base solo baja si el balance cae por debajo de él.
            self.base_principal = min(self.base_principal, self.balance.amount)

    def configure_cap(
        self,
        max_balance: Optional[Decimal],
        overflow_action: Optional[OverflowAction] = None,
        overflow_position_id: Optional[int] = None,
    ) -> Money:
        """Cambia el tope y su destino, y devuelve el excedente a desbordar ya.

        Poner un tope por debajo del saldo actual no espera al job del día
        siguiente: el excedente sale en el mismo momento.
        """
        self._ensure_active()
        self.max_balance, self.overflow_action, self.overflow_position_id = (
            self._normalize_cap_config(
                position_type=self.position_type,
                max_balance=max_balance,
                overflow_action=overflow_action,
                overflow_position_id=overflow_position_id,
                position_id=self.id,
            )
        )

        if self.max_balance is None or self.balance.amount <= self.max_balance:
            return self._zero()

        excess = Money(self.balance.amount - self.max_balance, self.balance.currency)
        self.balance = Money(self.max_balance, self.balance.currency)
        if self.base_principal is not None:
            self.base_principal = min(self.base_principal, self.balance.amount)
        return excess

    def clear_overflow_target(self) -> None:
        """El apartado destino dejó de existir: el excedente pasa al saldo
        disponible en vez de heredar la cadena del destino, para no alargar
        cadenas que el usuario nunca configuró."""
        if self.overflow_action == OverflowAction.TO_POSITION:
            self.overflow_action = OverflowAction.TO_AVAILABLE
            self.overflow_position_id = None

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
