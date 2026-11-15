"""Registrar, editar y borrar operaciones: dinero en la cuenta, transacciones, tenencia y
seguimiento del valor."""

from datetime import date
from types import SimpleNamespace
from decimal import Decimal
from typing import cast

import pytest
from sqlalchemy import select

from application.securities.commands.delete_trade import (
    DeleteTradeCommand,
    DeleteTradeHandler,
)
from application.securities.commands.record_trade import (
    RecordTradeCommand,
    RecordTradeHandler,
)
from application.securities.commands.update_trade import (
    UpdateTradeCommand,
    UpdateTradeHandler,
)
from application.securities.queries.list_holdings import (
    GetHoldingQuery,
    HoldingQueries,
    ListHoldingsQuery,
)
from application.securities.queries.list_trades import ListTradesHandler, ListTradesQuery
from application.securities.services.trade_bookkeeper import TradeBookkeeper
from application.securities.services.valuation import HoldingValuer
from application.transactions.commands.delete_transaction import (
    DeleteTransactionCommand,
    DeleteTransactionHandler,
)
from domain.entities.securities.exchange_rate import ExchangeRate
from domain.entities.securities.instrument import Instrument
from domain.entities.securities.instrument_price import InstrumentPrice
from domain.objects.enums import (
    AccountType,
    HoldingStatus,
    InstrumentType,
    Market,
    TradeType,
    TransactionType,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.models.account import AccountModel
from infrastructure.database.models.category import CategoryModel
from infrastructure.database.models.transaction import TransactionModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)
from infrastructure.database.repositories.sqlalchemy_installment_purchase_repository import (
    SQLAlchemyInstallmentPurchaseRepository,
)
from infrastructure.database.repositories.sqlalchemy_instrument_repository import (
    SQLAlchemyInstrumentRepository,
)
from infrastructure.database.repositories.sqlalchemy_price_repository import (
    SQLAlchemyExchangeRateRepository,
    SQLAlchemyInstrumentPriceRepository,
)
from infrastructure.database.repositories.sqlalchemy_trade_repository import (
    SQLAlchemySecurityHoldingRepository,
    SQLAlchemySecurityTradeRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from shared.exceptions.domain import (
    AccountNotFoundError,
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidSecurityTradeError,
    SecurityAccountTypeNotAllowedError,
    SecurityCurrencyMismatchError,
    SecurityTradeTransactionLockedError,
)

D = Decimal
TODAY = date(2026, 11, 14)
USER_ID = 4242


class SavepointUnitOfWork(AbstractUnitOfWork):
    """Cada handler en un savepoint: un error deshace lo que escribió, como en producción,
    sin cerrar la transacción de la prueba."""

    def __init__(self, db):
        self.db = db
        self._nested = None

    async def __aenter__(self):
        self._nested = await self.db.begin_nested()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        if self._nested is not None and self._nested.is_active:
            await self._nested.commit()

    async def rollback(self) -> None:
        if self._nested is not None and self._nested.is_active:
            await self._nested.rollback()


class Env:
    def __init__(self, db):
        self.db = db
        self.accounts = SQLAlchemyAccountRepository(db)
        self.instruments = SQLAlchemyInstrumentRepository(db)
        self.trades = SQLAlchemySecurityTradeRepository(db)
        self.holdings = SQLAlchemySecurityHoldingRepository(db)
        self.prices = SQLAlchemyInstrumentPriceRepository(db)
        self.fx = SQLAlchemyExchangeRateRepository(db)
        self.transactions = SQLAlchemyTransactionRepository(db)
        self.books = TradeBookkeeper(
            account_repository=self.accounts,
            transaction_repository=self.transactions,
            category_repository=SQLAlchemyCategoryRepository(db),
            instrument_repository=self.instruments,
            trade_repository=self.trades,
            holding_repository=self.holdings,
        )

    def uow(self):
        return SavepointUnitOfWork(self.db)

    async def record(self, account, instrument, kind=TradeType.BUY, day=3, **fields):
        handler = RecordTradeHandler(
            bookkeeper=self.books, uow=self.uow(), today=lambda: TODAY
        )
        return await handler.handle(
            RecordTradeCommand(
                user_id=USER_ID,
                account_uuid=account.uuid,
                instrument_uuid=instrument.uuid,
                trade_type=kind,
                trade_date=date(2026, 11, day),
                **fields,
            )
        )

    async def update(self, trade_uuid, day=3, **fields):
        handler = UpdateTradeHandler(
            bookkeeper=self.books, uow=self.uow(), today=lambda: TODAY
        )
        return await handler.handle(
            UpdateTradeCommand(
                user_id=USER_ID,
                trade_uuid=trade_uuid,
                trade_date=date(2026, 11, day),
                **fields,
            )
        )

    async def delete(self, trade_uuid):
        handler = DeleteTradeHandler(bookkeeper=self.books, uow=self.uow())
        return await handler.handle(
            DeleteTradeCommand(user_id=USER_ID, trade_uuid=trade_uuid)
        )

    async def balance(self, account) -> Decimal:
        self.db.expire_all()
        current = await self.accounts.get_by_id(account.id)
        assert current is not None
        return current.current_balance.amount

    async def movements(self, account) -> list[TransactionModel]:
        result = await self.db.execute(
            select(TransactionModel)
            .where(TransactionModel.account_id == account.id)
            .order_by(TransactionModel.id)
        )
        return list(result.scalars())

    def queries(self) -> HoldingQueries:
        return HoldingQueries(
            account_repository=self.accounts,
            instrument_repository=self.instruments,
            holding_repository=self.holdings,
            trade_repository=self.trades,
            valuer=HoldingValuer(price_repository=self.prices, fx_repository=self.fx),
            today=lambda: TODAY,
        )


@pytest.fixture
async def env(db_session):
    db_session.add(
        UserModel(id=USER_ID, uuid="trades-user", name="Trader", email="t@example.com")
    )
    await db_session.flush()
    return Env(db_session)


async def make_account(env, *, balance="10000", currency="MXN", kind=AccountType.INVESTMENT):
    model = AccountModel(
        user_id=USER_ID,
        bank_id=1,
        name=f"Casa de bolsa {currency}",
        type=kind,
        current_balance=D(balance),
        currency=currency,
    )
    env.db.add(model)
    await env.db.flush()
    # Plano, no el modelo: un rollback de savepoint expira los modelos de la sesión.
    return SimpleNamespace(id=model.id, uuid=model.uuid)


async def make_instrument(env, symbol="WALMEX*", market=Market.BMV, currency="MXN"):
    return await env.instruments.save(
        Instrument(
            id=None,
            uuid=None,
            market=market,
            symbol=symbol,
            name=symbol,
            instrument_type=InstrumentType.STOCK,
            currency=currency,
        )
    )


@pytest.fixture
async def account(env):
    return await make_account(env)


@pytest.fixture
async def walmex(env):
    return await make_instrument(env)


class TestRecord:
    async def test_buy_takes_money_and_opens_the_holding(self, env, account, walmex):
        result = await env.record(
            account, walmex, quantity=D("10"), price=D("54.79"), fees=D("11.60")
        )

        assert result.account_available_balance == D("9440.50")
        assert await env.balance(account) == D("9440.50")
        assert result.trade.cash_amount == D("559.50")
        assert result.holding.quantity == D("10")
        assert result.holding.avg_cost == D("55.950000")
        assert result.holding.status is HoldingStatus.OPEN

        [movement] = await env.movements(account)
        assert movement.type == TransactionType.TRANSFER
        assert movement.amount == D("559.50")
        assert movement.transaction_date == date(2026, 11, 3)
        assert movement.description == "Compra de 10 WALMEX*"

        tracked = await env.instruments.get_by_id(walmex.id)
        assert tracked.tracked_since == date(2026, 11, 3)

    async def test_an_earlier_trade_moves_tracking_back(self, env, account, walmex):
        await env.record(account, walmex, day=10, quantity=D("1"), price=D("50"))
        await env.record(account, walmex, day=2, quantity=D("1"), price=D("50"))
        assert (await env.instruments.get_by_id(walmex.id)).tracked_since == date(
            2026, 11, 2
        )

    async def test_sell_returns_money_and_realizes(self, env, account, walmex):
        await env.record(account, walmex, quantity=D("10"), price=D("50"), fees=D("10"))
        result = await env.record(
            account,
            walmex,
            TradeType.SELL,
            day=5,
            quantity=D("4"),
            price=D("60"),
            fees=D("5"),
            tax_withheld=D("2"),
        )
        # 240 − 5 − 2 entran; ganancia 240 − 5 − 4 × 51 = 31
        assert await env.balance(account) == D("10000") - D("510") + D("233")
        assert result.holding.realized_pnl == D("31.00")
        assert result.holding.quantity == D("6")
        movements = await env.movements(account)
        assert movements[-1].description == "Venta de 4 WALMEX*"

    async def test_dividend_is_income_in_investments(self, env, account, walmex):
        env.db.add(CategoryModel(name="Inversiones", type="INCOME", icon="i", color="#000"))
        await env.db.flush()
        await env.record(account, walmex, quantity=D("10"), price=D("50"))
        result = await env.record(
            account,
            walmex,
            TradeType.DIVIDEND,
            day=6,
            gross_amount=D("20.00"),
            tax_withheld=D("2.00"),
        )
        assert result.holding.dividends == D("18.00")
        dividend = (await env.movements(account))[-1]
        assert dividend.type == TransactionType.INCOME
        assert dividend.amount == D("18.00")
        assert dividend.category_id is not None
        assert dividend.description == "Dividendo de WALMEX*"

    async def test_split_moves_no_money(self, env, account, walmex):
        await env.record(account, walmex, quantity=D("10"), price=D("50"))
        result = await env.record(
            account, walmex, TradeType.SPLIT, day=6, split_from=1, split_to=2
        )
        assert result.holding.quantity == D("20")
        assert result.holding.avg_cost == D("25.000000")
        assert len(await env.movements(account)) == 1

    async def test_insufficient_funds_saves_nothing(self, env, walmex):
        poor = await make_account(env, balance="100")
        with pytest.raises(InsufficientFundsError):
            await env.record(poor, walmex, quantity=D("10"), price=D("50"))
        assert await env.balance(poor) == D("100")
        assert await env.trades.list_for_holding(poor.id, walmex.id) == []
        assert await env.holdings.get(poor.id, walmex.id) is None
        assert await env.movements(poor) == []

    async def test_cannot_sell_what_is_not_there(self, env, account, walmex):
        with pytest.raises(InsufficientSharesError):
            await env.record(
                account, walmex, TradeType.SELL, quantity=D("1"), price=D("50")
            )
        assert await env.balance(account) == D("10000")
        assert await env.movements(account) == []

    async def test_currency_must_match(self, env, account):
        aapl = await make_instrument(env, "AAPL", Market.US, "USD")
        with pytest.raises(SecurityCurrencyMismatchError):
            await env.record(account, aapl, quantity=D("1"), price=D("200"))

        dollars = await make_account(env, balance="1000", currency="USD")
        result = await env.record(dollars, aapl, quantity=D("1"), price=D("200"))
        assert result.account_available_balance == D("800")

    async def test_credit_cards_cannot_hold_securities(self, env, walmex):
        card = await make_account(env, kind=AccountType.CREDIT_CARD)
        with pytest.raises(SecurityAccountTypeNotAllowedError):
            await env.record(card, walmex, quantity=D("1"), price=D("50"))

    async def test_future_dates_are_rejected(self, env, account, walmex):
        with pytest.raises(InvalidSecurityTradeError, match="futura"):
            await env.record(account, walmex, day=15, quantity=D("1"), price=D("50"))

    async def test_other_users_account(self, env, walmex):
        env.db.add(UserModel(id=4243, uuid="other", name="Other", email="o@example.com"))
        await env.db.flush()
        model = AccountModel(
            user_id=4243, bank_id=1, name="Ajena", type=AccountType.INVESTMENT,
            current_balance=D("100"), currency="MXN",
        )
        env.db.add(model)
        await env.db.flush()
        other = SimpleNamespace(id=model.id, uuid=model.uuid)
        with pytest.raises(AccountNotFoundError):
            await env.record(other, walmex, quantity=D("1"), price=D("50"))


class TestUpdate:
    async def test_adjusts_money_by_the_difference(self, env, account, walmex):
        bought = await env.record(account, walmex, quantity=D("10"), price=D("50"))
        result = await env.update(bought.trade.uuid, quantity=D("12"), price=D("50"))

        assert await env.balance(account) == D("9400")
        assert result.holding.quantity == D("12")
        [movement] = await env.movements(account)
        assert movement.amount == D("600.00")
        assert movement.description == "Compra de 12 WALMEX*"

    async def test_editing_an_old_sale_only_needs_the_difference(self, env, walmex):
        account = await make_account(env, balance="500")
        await env.record(account, walmex, quantity=D("10"), price=D("50"))
        sold = await env.record(
            account, walmex, TradeType.SELL, day=5, quantity=D("10"), price=D("60")
        )
        # Se gasta lo de la venta: el disponible queda en 0.
        await env.record(account, await make_instrument(env, "FUNO11"), quantity=D("10"), price=D("60"))
        assert await env.balance(account) == 0

        result = await env.update(sold.trade.uuid, day=5, quantity=D("10"), price=D("61"))
        assert result.account_available_balance == D("10")
        with pytest.raises(InsufficientFundsError):
            await env.update(sold.trade.uuid, day=5, quantity=D("10"), price=D("50"))

    async def test_rejects_edits_that_leave_a_later_sale_short(self, env, account, walmex):
        bought = await env.record(account, walmex, quantity=D("10"), price=D("50"))
        await env.record(account, walmex, TradeType.SELL, day=5, quantity=D("8"), price=D("55"))
        balance = await env.balance(account)

        with pytest.raises(InsufficientSharesError):
            await env.update(bought.trade.uuid, quantity=D("5"), price=D("50"))
        with pytest.raises(InsufficientSharesError):
            await env.update(bought.trade.uuid, day=6, quantity=D("10"), price=D("50"))

        assert await env.balance(account) == balance
        holding = await env.holdings.get(account.id, walmex.id)
        assert holding.quantity == D("2")

    async def test_changing_a_dividend(self, env, account, walmex):
        await env.record(account, walmex, quantity=D("10"), price=D("50"))
        dividend = await env.record(
            account, walmex, TradeType.DIVIDEND, day=6, gross_amount=D("20.00")
        )
        result = await env.update(dividend.trade.uuid, day=6, gross_amount=D("25.00"))
        assert result.holding.dividends == D("25.00")
        assert await env.balance(account) == D("9525.00")


class TestDelete:
    async def test_reverses_the_money_and_drops_the_empty_holding(
        self, env, account, walmex
    ):
        bought = await env.record(account, walmex, quantity=D("10"), price=D("50"))
        result = await env.delete(bought.trade.uuid)

        assert result.trade is None and result.holding is None
        assert await env.balance(account) == D("10000")
        assert await env.movements(account) == []
        assert await env.holdings.get(account.id, walmex.id) is None

    async def test_cannot_delete_the_buy_behind_a_sale(self, env, account, walmex):
        bought = await env.record(account, walmex, quantity=D("10"), price=D("50"))
        await env.record(account, walmex, TradeType.SELL, day=5, quantity=D("10"), price=D("55"))
        with pytest.raises(InsufficientSharesError):
            await env.delete(bought.trade.uuid)
        assert len(await env.movements(account)) == 2

    async def test_deleting_a_sale_reopens(self, env, account, walmex):
        await env.record(account, walmex, quantity=D("10"), price=D("50"))
        sold = await env.record(
            account, walmex, TradeType.SELL, day=5, quantity=D("10"), price=D("55")
        )
        result = await env.delete(sold.trade.uuid)
        assert result.holding.status is HoldingStatus.OPEN
        assert result.holding.realized_pnl == D("0.00")
        assert await env.balance(account) == D("9500")


class TestTransactionGuard:
    async def test_dividend_transaction_cannot_be_deleted_from_transactions(
        self, env, account, walmex
    ):
        await env.record(account, walmex, quantity=D("10"), price=D("50"))
        await env.record(account, walmex, TradeType.DIVIDEND, day=6, gross_amount=D("20"))
        dividend = (await env.movements(account))[-1]

        handler = DeleteTransactionHandler(
            env.transactions,
            env.accounts,
            SQLAlchemyInstallmentPurchaseRepository(env.db),
            env.uow(),
            security_trade_repository=env.trades,
        )
        with pytest.raises(SecurityTradeTransactionLockedError):
            await handler.handle(
                DeleteTransactionCommand(uuid=dividend.uuid, user_id=USER_ID)
            )


class TestQueries:
    async def test_values_holdings_with_the_last_close_and_fx(self, env, account, walmex):
        await env.record(account, walmex, quantity=D("10"), price=D("50"), fees=D("10"))
        dollars = await make_account(env, balance="1000", currency="USD")
        aapl = await make_instrument(env, "AAPL", Market.US, "USD")
        await env.record(dollars, aapl, quantity=D("2"), price=D("200"))
        await env.prices.save_many(
            [
                InstrumentPrice(instrument_id=walmex.id, price_date=date(2026, 11, 12), close=D("55"), provider="databursatil"),
                InstrumentPrice(instrument_id=walmex.id, price_date=date(2026, 11, 13), close=D("56"), provider="databursatil"),
                InstrumentPrice(instrument_id=walmex.id, price_date=date(2026, 11, 16), close=D("99"), provider="databursatil"),
                InstrumentPrice(instrument_id=aapl.id, price_date=date(2026, 11, 13), close=D("210"), provider="twelvedata"),
            ]
        )
        await env.fx.save_many(
            [ExchangeRate(base="USD", quote="MXN", rate_date=date(2026, 11, 13), rate=D("18.5525"), provider="banxico")]
        )

        holdings = {
            h.instrument.symbol: h
            for h in await env.queries().list_holdings(ListHoldingsQuery(user_id=USER_ID))
        }

        w = holdings["WALMEX*"]
        assert (w.last_price, w.last_price_date) == (D("56.000000"), date(2026, 11, 13))
        assert w.market_value == D("560.00")
        assert w.unrealized_pnl == D("50.00")
        assert w.unrealized_pnl_pct == D("9.80")
        assert (w.fx_rate, w.market_value_mxn) == (None, D("560.00"))

        a = holdings["AAPL"]
        assert a.market_value == D("420.00")
        assert a.fx_rate == D("18.55250000")
        assert a.market_value_mxn == D("7792.05")

    async def test_holding_without_prices_has_no_valuation(self, env, account, walmex):
        await env.record(account, walmex, quantity=D("1"), price=D("50"))
        [holding] = await env.queries().list_holdings(ListHoldingsQuery(user_id=USER_ID))
        assert holding.market_value is None and holding.cost_basis == D("50.00")

    async def test_closed_holdings_are_hidden_by_default(self, env, account, walmex):
        await env.record(account, walmex, quantity=D("1"), price=D("50"))
        await env.record(account, walmex, TradeType.SELL, day=4, quantity=D("1"), price=D("50"))
        assert await env.queries().list_holdings(ListHoldingsQuery(user_id=USER_ID)) == []
        [closed] = await env.queries().list_holdings(
            ListHoldingsQuery(user_id=USER_ID, include_closed=True)
        )
        detail = await env.queries().get_holding(
            GetHoldingQuery(user_id=USER_ID, holding_uuid=closed.uuid)
        )
        assert [t.trade_type for t in detail.trades] == [TradeType.SELL, TradeType.BUY]

    async def test_list_trades_newest_first(self, env, account, walmex):
        await env.record(account, walmex, day=2, quantity=D("1"), price=D("50"))
        await env.record(account, walmex, day=4, quantity=D("1"), price=D("51"))
        handler = ListTradesHandler(
            account_repository=env.accounts,
            instrument_repository=env.instruments,
            trade_repository=env.trades,
        )
        trades = await handler.handle(
            ListTradesQuery(user_id=USER_ID, account_uuid=cast(str, account.uuid))
        )
        assert [t.trade_date.day for t in trades] == [4, 2]
        assert trades[0].account_uuid == account.uuid
