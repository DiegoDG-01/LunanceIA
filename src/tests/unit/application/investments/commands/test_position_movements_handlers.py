"""Unit tests for DepositToPosition, WithdrawFromPosition and LiquidatePosition handlers."""

import pytest
from dataclasses import replace
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import cast

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
from application.investments.services.position_overflow import PositionOverflowService
from application.dto.investment_position_dto import (
    LiquidatePositionDTO,
    PositionMovementDTO,
)
from domain.entities.account import Account
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import (
    AccountType,
    OverflowAction,
    PositionStatus,
    PositionType,
)
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
    position_repo.get_by_overflow_target = AsyncMock(return_value=[])

    transaction_repo = MagicMock()
    transaction_repo.create = AsyncMock(side_effect=lambda t: t)

    notification_repo = MagicMock()
    notification_repo.create = AsyncMock()

    return {
        "user_repo": user_repo,
        "account_repo": account_repo,
        "position_repo": position_repo,
        "transaction_repo": transaction_repo,
        "notification_repo": notification_repo,
        "overflow_service": PositionOverflowService(position_repository=position_repo),
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
        handler = DepositToPositionHandler(**_handler_kwargs(mocks, overflow=True))

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
        handler = DepositToPositionHandler(**_handler_kwargs(mocks, overflow=True))

        with pytest.raises(InsufficientFundsError):
            await handler.handle(DepositToPositionCommand(movement_dto("300.00")))

        mocks["uow"].commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_deposit_to_fixed_term_raises(self):
        account = make_account()
        position = make_position(position_type=PositionType.FIXED_TERM, term_days=90)
        mocks = build_mocks(account, position)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks, overflow=True))

        with pytest.raises(FixedTermDepositNotAllowedError):
            await handler.handle(DepositToPositionCommand(movement_dto()))

    @pytest.mark.asyncio
    async def test_position_not_found_raises(self):
        mocks = build_mocks(make_account(), make_position())
        mocks["position_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks, overflow=True))

        with pytest.raises(InvestmentPositionNotFoundError):
            await handler.handle(DepositToPositionCommand(movement_dto()))


@pytest.mark.unit
class TestWithdrawFromPositionHandler:
    @pytest.mark.asyncio
    async def test_withdraw_returns_money_to_available(self):
        account, position = make_account("500.00"), make_position()
        mocks = build_mocks(account, position)
        handler = WithdrawFromPositionHandler(**_handler_kwargs(mocks, overflow=True))

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
        handler = WithdrawFromPositionHandler(**_handler_kwargs(mocks, overflow=True))

        with pytest.raises(InsufficientFundsError):
            await handler.handle(WithdrawFromPositionCommand(movement_dto("1000.01")))

        mocks["uow"].commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_withdraw_from_fixed_term_raises(self):
        account = make_account()
        position = make_position(position_type=PositionType.FIXED_TERM, term_days=90)
        mocks = build_mocks(account, position)
        handler = WithdrawFromPositionHandler(**_handler_kwargs(mocks, overflow=True))

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
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks, notifications=True))

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
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks, notifications=True))

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
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks, notifications=True))

        with pytest.raises(InvestmentPositionLockedError):
            await handler.handle(LiquidatePositionCommand(self._dto()))

        mocks["uow"].commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_already_liquidated_position_raises(self):
        account = make_account()
        position = make_position()
        position.liquidate(date.today())
        mocks = build_mocks(account, position)
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks, notifications=True))

        with pytest.raises(InvestmentPositionNotActiveError):
            await handler.handle(LiquidatePositionCommand(self._dto()))


@pytest.mark.unit
class TestLiquidationRepairsChains:
    """Test what happens to the positions that overflowed into the liquidated one."""

    def _dto(self) -> LiquidatePositionDTO:
        return LiquidatePositionDTO(user_id=1, position_uuid="pos-1")

    def _source_pointing_at(self, target_id: int):
        return replace(
            make_position(
                max_balance=Decimal("1000.00"),
                overflow_action=OverflowAction.TO_POSITION,
                overflow_position_id=target_id,
            ),
            id=7,
            uuid="pos-7",
        )

    @pytest.mark.asyncio
    async def test_source_falls_back_to_available(self):
        account, position = make_account("500.00"), make_position()
        source = self._source_pointing_at(cast(int, position.id))
        mocks = build_mocks(account, position)
        mocks["position_repo"].get_by_overflow_target = AsyncMock(return_value=[source])
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks, notifications=True))

        await handler.handle(LiquidatePositionCommand(self._dto()))

        assert source.overflow_action == OverflowAction.TO_AVAILABLE
        assert source.overflow_position_id is None
        # El tope se respeta: solo cambia a dónde va el excedente.
        assert source.max_balance == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_source_does_not_inherit_the_chain(self):
        account, position = make_account("500.00"), make_position()
        position.overflow_action = OverflowAction.TO_POSITION
        position.overflow_position_id = 9
        source = self._source_pointing_at(cast(int, position.id))
        mocks = build_mocks(account, position)
        mocks["position_repo"].get_by_overflow_target = AsyncMock(return_value=[source])
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks, notifications=True))

        await handler.handle(LiquidatePositionCommand(self._dto()))

        assert source.overflow_position_id is None

    @pytest.mark.asyncio
    async def test_the_user_is_told(self):
        account, position = make_account("500.00"), make_position()
        source = self._source_pointing_at(cast(int, position.id))
        mocks = build_mocks(account, position)
        mocks["position_repo"].get_by_overflow_target = AsyncMock(return_value=[source])
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks, notifications=True))

        await handler.handle(LiquidatePositionCommand(self._dto()))

        mocks["notification_repo"].create.assert_awaited_once()
        notification = mocks["notification_repo"].create.call_args.args[0]
        assert notification.user_id == 1
        assert "Cajita vacaciones" in notification.message

    @pytest.mark.asyncio
    async def test_no_sources_means_no_notifications(self):
        account, position = make_account("500.00"), make_position()
        mocks = build_mocks(account, position)
        handler = LiquidatePositionHandler(**_handler_kwargs(mocks, notifications=True))

        await handler.handle(LiquidatePositionCommand(self._dto()))

        mocks["notification_repo"].create.assert_not_called()


def build_chain_mocks(account, *positions):
    """Like build_mocks, but resolves several positions by id and uuid."""
    mocks = build_mocks(account, positions[0])
    by_id = {p.id: p for p in positions}
    by_uuid = {p.uuid: p for p in positions}
    mocks["position_repo"].get_by_id = AsyncMock(
        side_effect=lambda position_id, **_: by_id.get(position_id)
    )
    mocks["position_repo"].get_by_uuid_and_user_id = AsyncMock(
        side_effect=lambda position_uuid, user_id, **_: by_uuid.get(position_uuid)
    )
    return mocks


@pytest.mark.unit
class TestDepositWithCap:
    """Test deposits into a capped position and its overflow chain."""

    @pytest.mark.asyncio
    async def test_deposit_over_the_cap_returns_the_rest_to_available(self):
        account = make_account("1000.00")
        position = make_position(max_balance=Decimal("1200.00"))
        mocks = build_mocks(account, position)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks, overflow=True))

        await handler.handle(DepositToPositionCommand(movement_dto("500.00")))

        assert position.balance.amount == Decimal("1200.00")
        # Solo los 200 que cupieron salieron del disponible.
        assert account.current_balance.amount == Decimal("800.00")
        movement = mocks["transaction_repo"].create.call_args.args[0]
        assert movement.amount.amount == Decimal("200.00")

    @pytest.mark.asyncio
    async def test_deposit_into_a_full_position_moves_nothing(self):
        account = make_account("1000.00")
        position = make_position(max_balance=Decimal("1000.00"))
        mocks = build_mocks(account, position)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks, overflow=True))

        await handler.handle(DepositToPositionCommand(movement_dto("500.00")))

        assert position.balance.amount == Decimal("1000.00")
        assert account.current_balance.amount == Decimal("1000.00")
        mocks["transaction_repo"].create.assert_not_called()

    @pytest.mark.asyncio
    async def test_chain_absorbs_the_excess_without_touching_available(self):
        account = make_account("1000.00")
        target = replace(make_position(), id=6, uuid="pos-6")
        position = replace(
            make_position(
                max_balance=Decimal("1200.00"),
                overflow_action=OverflowAction.TO_POSITION,
                overflow_position_id=6,
            ),
            id=5,
            uuid="pos-1",
        )
        mocks = build_chain_mocks(account, position, target)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks, overflow=True))

        await handler.handle(DepositToPositionCommand(movement_dto("500.00")))

        assert position.balance.amount == Decimal("1200.00")
        assert target.balance.amount == Decimal("1300.00")
        # Los 500 completos salieron del disponible, aunque se repartieron.
        assert account.current_balance.amount == Decimal("500.00")
        movement = mocks["transaction_repo"].create.call_args.args[0]
        assert movement.amount.amount == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_response_exposes_the_chain_target(self):
        account = make_account("1000.00")
        target = replace(make_position(), id=6, uuid="pos-6")
        position = replace(
            make_position(
                max_balance=Decimal("5000.00"),
                overflow_action=OverflowAction.TO_POSITION,
                overflow_position_id=6,
            ),
            id=5,
            uuid="pos-1",
        )
        mocks = build_chain_mocks(account, position, target)
        handler = DepositToPositionHandler(**_handler_kwargs(mocks, overflow=True))

        result = await handler.handle(DepositToPositionCommand(movement_dto("100.00")))

        assert result.overflow_position_uuid == "pos-6"


def _handler_kwargs(mocks, overflow: bool = False, notifications: bool = False) -> dict:
    kwargs = {
        "user_repository": mocks["user_repo"],
        "account_repository": mocks["account_repo"],
        "position_repository": mocks["position_repo"],
        "transaction_repository": mocks["transaction_repo"],
        "uow": mocks["uow"],
    }
    if overflow:
        kwargs["overflow_service"] = mocks["overflow_service"]
    if notifications:
        kwargs["notification_repository"] = mocks["notification_repo"]
    return kwargs
