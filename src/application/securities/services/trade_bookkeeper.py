"""Lo que comparten registrar, editar y borrar una operación: bloquear la cuenta, mover el
dinero y recalcular la tenencia.

Orden de bloqueo: cuenta → tenencia (el mismo de cuenta → apartado).

Después de bloquear la cuenta, todo lo que decide el resultado se lee con bloqueo (la
operación, sus hermanas, la tenencia) y la transacción anterior se borra con un DELETE. En
MySQL con REPEATABLE READ, una lectura sin bloqueo ve la foto que la transacción tomó en su
primera lectura, y esa ya ocurrió antes de esperar a la cuenta (al cargar el usuario de la
petición): una compra simultánea en la misma cuenta no vería la otra y recalcularía la
tenencia sin ella.

El dinero se ajusta por la diferencia entre el efecto anterior y el nuevo, así que editar
una venta vieja no exige tener otra vez todo lo que se recibió, solo lo que cambia. La
transacción anterior se borra y se crea otra con los datos nuevos.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import cast

from domain.entities.accounts.account import Account
from domain.entities.securities.instrument import Instrument
from domain.entities.securities.security_holding import SecurityHolding
from domain.entities.securities.security_trade import SecurityTrade
from domain.entities.transactions.transaction import Transaction
from domain.objects.enums import AccountType, CategoryName, TradeType, TransactionType
from domain.objects.money import Money
from domain.repositories.accounts.account_repository import AccountRepository
from domain.repositories.categories.category_repository import CategoryRepository
from domain.repositories.securities.instrument_repository import InstrumentRepository
from domain.repositories.securities.trade_repository import (
    SecurityHoldingRepository,
    SecurityTradeRepository,
)
from domain.repositories.transactions.transaction_repository import (
    TransactionRepository,
)
from domain.services.holding_ledger import replay
from shared.exceptions.domain import (
    AccountInactiveError,
    AccountNotFoundError,
    InstrumentNotFoundError,
    InsufficientFundsError,
    InvalidSecurityTradeError,
    SecurityAccountTypeNotAllowedError,
    SecurityCurrencyMismatchError,
)

ZERO = Decimal(0)


def cash_effect(trade: SecurityTrade | None) -> Decimal:
    """Cuánto cambia el disponible por la operación (negativo si sale dinero)."""
    if trade is None or not trade.moves_money:
        return ZERO
    if trade.trade_type is TradeType.BUY:
        return -trade.cash_amount
    return trade.cash_amount


def _quantity(value: Decimal) -> str:
    return f"{value.normalize():f}"


def describe(trade: SecurityTrade, instrument: Instrument) -> str:
    if trade.trade_type is TradeType.BUY:
        return f"Compra de {_quantity(trade.quantity)} {instrument.symbol}"
    if trade.trade_type is TradeType.SELL:
        return f"Venta de {_quantity(trade.quantity)} {instrument.symbol}"
    return f"Dividendo de {instrument.symbol}"


@dataclass(frozen=True, slots=True)
class TradeContext:
    account: Account
    instrument: Instrument


class TradeBookkeeper:
    def __init__(
        self,
        *,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        category_repository: CategoryRepository,
        instrument_repository: InstrumentRepository,
        trade_repository: SecurityTradeRepository,
        holding_repository: SecurityHoldingRepository,
    ) -> None:
        self.accounts = account_repository
        self.transactions = transaction_repository
        self.categories = category_repository
        self.instruments = instrument_repository
        self.trades = trade_repository
        self.holdings = holding_repository

    async def lock(
        self, *, account_id: int, user_id: int, instrument_id: int
    ) -> TradeContext:
        account = await self.accounts.get_by_id(account_id, for_update=True)
        if account is None or account.user_id != user_id:
            raise AccountNotFoundError(str(account_id))
        if not account.is_active:
            raise AccountInactiveError(account_id)
        if account.account_type is AccountType.CREDIT_CARD:
            raise SecurityAccountTypeNotAllowedError(account.account_type.value)
        instrument = await self.instruments.get_by_id(instrument_id)
        if instrument is None:
            raise InstrumentNotFoundError(str(instrument_id))
        if account.current_balance.currency != instrument.currency:
            raise SecurityCurrencyMismatchError(
                account.current_balance.currency, instrument.currency
            )
        return TradeContext(account=account, instrument=instrument)

    @staticmethod
    def check_date(trade: SecurityTrade, today: date) -> None:
        if trade.trade_date > today:
            raise InvalidSecurityTradeError("la fecha no puede ser futura")

    async def move_money(
        self,
        context: TradeContext,
        *,
        old: SecurityTrade | None,
        new: SecurityTrade | None,
    ) -> int | None:
        """Ajusta el disponible de `old` a `new` y deja una transacción para `new`.
        Devuelve el id de esa transacción (None en un split o al borrar)."""
        account = context.account
        old_applied = old is not None and old.transaction_id is not None
        delta = cash_effect(new) - (cash_effect(old) if old_applied else ZERO)
        balance = account.current_balance.amount
        if balance + delta < 0:
            raise InsufficientFundsError(
                required_amount=float(-delta), available_amount=float(balance)
            )
        if delta != 0:
            account.update_balance(
                Money(balance + delta, account.current_balance.currency)
            )
            await self.accounts.update(account)

        if old_applied:
            await self.transactions.delete_bulk_by_ids(
                [cast(int, cast(SecurityTrade, old).transaction_id)], account.user_id
            )

        if new is None or not new.moves_money:
            return None
        category_id = None
        if new.trade_type is TradeType.DIVIDEND:
            category = await self.categories.get_by_name(CategoryName.INVERSIONES.value)
            category_id = category.id if category else None
        movement = Transaction.create_new(
            user_id=account.user_id,
            account_id=cast(int, account.id),
            category_id=category_id,
            transaction_type=(
                TransactionType.INCOME
                if new.trade_type is TradeType.DIVIDEND
                else TransactionType.TRANSFER
            ),
            amount=Money(new.cash_amount, account.current_balance.currency),
            transaction_date=new.trade_date,
            description=describe(new, context.instrument),
        )
        created = await self.transactions.create(movement)
        return created.id

    async def recompute(
        self, context: TradeContext, *, changed_from: date
    ) -> SecurityHolding | None:
        """Recalcula la tenencia con todas sus operaciones y marca sus fotos para rehacer
        desde `changed_from`. Lanza `InsufficientSharesError` si alguna venta o split se
        queda sin títulos. None si ya no quedan operaciones."""
        account_id = cast(int, context.account.id)
        instrument_id = cast(int, context.instrument.id)
        trades = await self.trades.list_for_holding(
            account_id, instrument_id, for_update=True
        )
        state = replay(trades, symbol=context.instrument.symbol)
        holding = await self.holdings.get(account_id, instrument_id, for_update=True)
        if state.trades == 0:
            if holding is not None:
                await self.holdings.delete(cast(int, holding.id))
            return None
        if holding is None:
            holding = SecurityHolding(
                id=None,
                uuid=None,
                user_id=context.account.user_id,
                account_id=account_id,
                instrument_id=instrument_id,
                quantity=ZERO,
                avg_cost=ZERO,
                cost_basis=ZERO,
                realized_pnl=ZERO,
                dividends=ZERO,
                status=state.status,
            )
        holding.quantity = state.quantity
        holding.avg_cost = state.avg_cost
        holding.cost_basis = state.cost_basis
        holding.realized_pnl = state.realized
        holding.dividends = state.dividends
        holding.status = state.status
        holding.opened_at = state.opened_at
        holding.closed_at = state.closed_at
        holding.mark_dirty_from(changed_from)
        return await self.holdings.save(holding)
