"""Unit tests for DepositToPosition, WithdrawFromPosition and LiquidatePosition handlers."""

import pytest
from dataclasses import replace
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from application.investments.commands.deposit_to_position import (
    DepositToPositionCommand,
    DepositToPositionHandler,
)
from application.investments.commands.withdraw_from_position import (
    WithdrawFromPositionCommand,
    WithdrawFromPositionHandler,
)
from application.investments.commands.liquidate_position import (
    LiquidatePositionCommand,
    LiquidatePositionHandler,
)
from application.dto.investment_position_dto import (
    LiquidatePositionDTO,
    PositionMovementDTO,
)
from domain.entities.account import Account
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import AccountType, PositionStatus, PositionType
from domain.objects.money import Money
from shared.exceptions.domain import (
    FixedTermDepositNotAllowedError,
    FixedTermWithdrawalNotAllowedError,
    InsufficientFundsError,
    InvestmentPositionLockedError,
    InvestmentPositionNotActiveError,
    InvestmentPositionNotFoundError,
)


def make_account(balance: str = "1000.00") -> Account:
    return Account(
        id=1,
        uuid="acc-1",
        user_id=1,
        bank_id=1,
        name="Cuenta SOFIPO",
        account_type=AccountType.SAVINGS,
        current_balance=Money(Decimal(balance)),
        is_active=True,
        creation_date=datetime.now(timezone.utc),
    )


def make_position(**overrides) -> InvestmentPosition:
    defaults = {
        "account_id": 1,
        "name": "Cajita vacaciones",
        "position_type": PositionType.ON_DEMAND,
        "initial_balance": Money(Decimal("1000.00")),
        "annual_rate": Decimal("10.00"),
        "start_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    position = InvestmentPosition.create_new(**defaults)
    return replace(position, id=5, uuid="pos-1")


def build_mocks(account, position):
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()

    user_repo = MagicMock()
    user_repo.get_by_id = AsyncMock(return_value=MagicMock(id=1, is_active=True))

    account_repo = MagicMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    account_repo.update = AsyncMock()

    position_repo = MagicMock()
    position_repo.get_by_uuid_and_user_id = AsyncMock(return_value=position)
    position_repo.get_by_id = AsyncMock(return_value=position)
    position_repo.update = AsyncMock()

    transaction_repo = MagicMock()
    transaction_repo.create = AsyncMock(side_effect=lambda t: t)

    return {
        "user_repo": user_repo,
        "account_repo": account_repo,
        "position_repo": position_repo,
        "transaction_repo": transaction_repo,
        "uow": uow,
    }


def movement_dto(amount: str = "100.00") -> PositionMovementDTO:
    return PositionMovementDTO(user_id=1, position_uuid="pos-1", amount=Decimal(amount))


@pytest.mark.unit
class TestDepositToPositionHandler:
    @pytest.mark.asyncio
    async def test_deposit_moves_money_from_available_to_position(self):
        account, position = make_account("1000.00"), make_position()
        mocks = build_mocks(account, position)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks))

        result = await handler.handle(DepositToPositionCommand(movement_dto("300.00")))

        assert position.balance.amount == Decimal("1300.00")
        assert account.current_balance.amount == Decimal("700.00")
        assert result.balance == Decimal("1300.00")
        assert result.account_available_balance == Decimal("700.00")
        movement = mocks["transaction_repo"].create.call_args.args[0]
        assert movement.position_id == 5
        mocks["uow"].commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deposit_more_than_available_raises(self):
        account, position = make_account("100.00"), make_position()
        mocks = build_mocks(account, position)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks))

        with pytest.raises(InsufficientFundsError):
            await handler.handle(DepositToPositionCommand(movement_dto("300.00")))

        mocks["uow"].commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_deposit_to_fixed_term_raises(self):
        account = make_account()
        position = make_position(position_type=PositionType.FIXED_TERM, term_days=90)
        mocks = build_mocks(account, position)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks))

        with pytest.raises(FixedTermDepositNotAllowedError):
            await handler.handle(DepositToPositionCommand(movement_dto()))

    @pytest.mark.asyncio
    async def test_position_not_found_raises(self):
        mocks = build_mocks(make_account(), make_position())
        mocks["position_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks))

        with pytest.raises(InvestmentPositionNotFoundError):
            await handler.handle(DepositToPositionCommand(movement_dto()))


@pytest.mark.unit
class TestWithdrawFromPositionHandler:
    @pytest.mark.asyncio
    async def test_withdraw_returns_money_to_available(self):
        account, position = make_account("500.00"), make_position()
        mocks = build_mocks(account, position)
        handler = WithdrawFromPositionHandler(**_handler_kwargs(mocks))

        result = await handler.handle(
            WithdrawFromPositionCommand(movement_dto("400.00"))
        )

        assert position.balance.amount == Decimal("600.00")
        assert account.current_balance.amount == Decimal("900.00")
        assert result.account_available_balance == Decimal("900.00")
        mocks["uow"].commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_withdraw_more_than_position_balance_raises(self):
        account, position = make_account(), make_position()
        mocks = build_mocks(account, position)
        handler = WithdrawFromPositionHandler(**_handler_kwargs(mocks))

        with pytest.raises(InsufficientFundsError):
            await handler.handle(WithdrawFromPositionCommand(movement_dto("1000.01")))

        mocks["uow"].commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_withdraw_from_fixed_term_raises(self):
        account = make_account()
        position = make_position(position_type=PositionType.FIXED_TERM, term_days=90)
        mocks = build_mocks(account, position)
        handler = WithdrawFromPositionHandler(**_handler_kwargs(mocks))

        with pytest.raises(FixedTermWithdrawalNotAllowedError):
            await handler.handle(WithdrawFromPositionCommand(movement_dto()))


@pytest.mark.unit
class TestLiquidatePositionHandler:
    def _dto(self) -> LiquidatePositionDTO:
        return LiquidatePositionDTO(user_id=1, position_uuid="pos-1")

    @pytest.mark.asyncio
    async def test_on_demand_liquidation_credits_full_value(self):
        account, position = make_account("500.00"), make_position()
        mocks = build_mocks(account, position)
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks))

        result = await handler.handle(LiquidatePositionCommand(self._dto()))

        assert result.payout_amount == Decimal("1000.00")
        assert result.status == PositionStatus.LIQUIDATED
        assert account.current_balance.amount == Decimal("1500.00")
        movement = mocks["transaction_repo"].create.call_args.args[0]
        assert movement.amount.amount == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_early_fixed_term_liquidation_applies_penalty(self):
        account = make_account("0.00")
        position = make_position(
            position_type=PositionType.FIXED_TERM,
            term_days=3650,
            early_withdrawal_penalty=Decimal("10.00"),
            start_date=date.today() - timedelta(days=30),
        )
        position.accrue_yield(Money(Decimal("100.00")))
        mocks = build_mocks(account, position)
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks))

        result = await handler.handle(LiquidatePositionCommand(self._dto()))

        # Capital 1000 intacto + rendimiento 100 castigado 10%
        assert result.payout_amount == Decimal("1090.00")
        assert account.current_balance.amount == Decimal("1090.00")

    @pytest.mark.asyncio
    async def test_liquidation_during_lock_period_raises(self):
        account = make_account()
        position = make_position(
            position_type=PositionType.FIXED_TERM,
            term_days=3650,
            start_date=date.today() - timedelta(days=30),
            lock_period_end_date=date.today() + timedelta(days=30),
        )
        mocks = build_mocks(account, position)
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks))

        with pytest.raises(InvestmentPositionLockedError):
            await handler.handle(LiquidatePositionCommand(self._dto()))

        mocks["uow"].commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_already_liquidated_position_raises(self):
        account = make_account()
        position = make_position()
        position.liquidate(date.today())
        mocks = build_mocks(account, position)
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks))

        with pytest.raises(InvestmentPositionNotActiveError):
            await handler.handle(LiquidatePositionCommand(self._dto()))


def _handler_kwargs(mocks) -> dict:
    return {
        "user_repository": mocks["user_repo"],
        "account_repository": mocks["account_repo"],
        "position_repository": mocks["position_repo"],
        "transaction_repository": mocks["transaction_repo"],
        "uow": mocks["uow"],
    }
