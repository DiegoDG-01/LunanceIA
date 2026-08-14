"""Unit tests for CreatePositionHandler."""

import pytest
from dataclasses import replace
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from application.investments.commands.create_position import (
    CreatePositionCommand,
    CreatePositionHandler,
)
from application.dto.investment_position_dto import CreatePositionDTO
from domain.entities.account import Account
from domain.objects.enums import AccountType, PositionStatus, PositionType
from domain.objects.money import Money
from shared.exceptions.domain import (
    AccountInactiveError,
    AccountNotFoundError,
    InsufficientFundsError,
    PositionAccountTypeNotAllowedError,
    UserNotFoundError,
)


def make_account(
    balance: str = "1000.00",
    account_type: AccountType = AccountType.SAVINGS,
    is_active: bool = True,
) -> Account:
    return Account(
        id=1,
        uuid="acc-1",
        user_id=1,
        bank_id=1,
        name="Cuenta SOFIPO",
        account_type=account_type,
        current_balance=Money(Decimal(balance)),
        is_active=is_active,
        creation_date=datetime.now(timezone.utc),
    )


def make_dto(**overrides) -> CreatePositionDTO:
    defaults = {
        "user_id": 1,
        "account_uuid": "acc-1",
        "name": "Cajita vacaciones",
        "position_type": PositionType.ON_DEMAND,
        "amount": Decimal("400.00"),
        "annual_rate": Decimal("10.00"),
    }
    defaults.update(overrides)
    return CreatePositionDTO(**defaults)


@pytest.mark.unit
class TestCreatePositionHandler:
    @pytest.fixture
    def mocks(self):
        uow = MagicMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()

        user_repo = MagicMock()
        user_repo.get_by_id = AsyncMock(return_value=MagicMock(id=1, is_active=True))

        position_repo = MagicMock()
        position_repo.create = AsyncMock(
            side_effect=lambda p: replace(p, id=5, uuid="pos-1")
        )

        account_repo = MagicMock()
        account_repo.update = AsyncMock()

        transaction_repo = MagicMock()
        transaction_repo.create = AsyncMock(side_effect=lambda t: t)

        return {
            "user_repo": user_repo,
            "account_repo": account_repo,
            "position_repo": position_repo,
            "transaction_repo": transaction_repo,
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return CreatePositionHandler(
            mocks["user_repo"],
            mocks["account_repo"],
            mocks["position_repo"],
            mocks["transaction_repo"],
            mocks["uow"],
        )

    def _wire_account(self, mocks, account):
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)

    @pytest.mark.asyncio
    async def test_creates_position_and_moves_money_from_available(
        self, handler, mocks
    ):
        account = make_account(balance="1000.00")
        self._wire_account(mocks, account)

        result = await handler.handle(CreatePositionCommand(make_dto()))

        assert account.current_balance.amount == Decimal("600.00")
        assert result.balance == Decimal("400.00")
        assert result.status == PositionStatus.ACTIVE
        assert result.account_available_balance == Decimal("600.00")
        assert result.position_uuid == "pos-1"

        movement = mocks["transaction_repo"].create.call_args.args[0]
        assert movement.position_id == 5
        assert movement.amount.amount == Decimal("400.00")
        mocks["uow"].commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fixed_term_passes_term_settings(self, handler, mocks):
        account = make_account()
        self._wire_account(mocks, account)
        dto = make_dto(
            position_type=PositionType.FIXED_TERM,
            term_days=90,
            early_withdrawal_penalty=Decimal("10.00"),
        )

        result = await handler.handle(CreatePositionCommand(dto))

        assert result.position_type == PositionType.FIXED_TERM
        assert result.term_days == 90
        assert result.maturity_date == result.start_date + timedelta(days=90)
        assert result.early_withdrawal_penalty == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_insufficient_available_funds_raises(self, handler, mocks):
        account = make_account(balance="100.00")
        self._wire_account(mocks, account)

        with pytest.raises(InsufficientFundsError):
            await handler.handle(CreatePositionCommand(make_dto()))

        mocks["uow"].commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_credit_card_account_raises(self, handler, mocks):
        account = make_account(account_type=AccountType.CREDIT_CARD)
        self._wire_account(mocks, account)

        with pytest.raises(PositionAccountTypeNotAllowedError):
            await handler.handle(CreatePositionCommand(make_dto()))

    @pytest.mark.asyncio
    async def test_inactive_account_raises(self, handler, mocks):
        account = make_account(is_active=False)
        self._wire_account(mocks, account)

        with pytest.raises(AccountInactiveError):
            await handler.handle(CreatePositionCommand(make_dto()))

    @pytest.mark.asyncio
    async def test_account_not_found_raises(self, handler, mocks):
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(CreatePositionCommand(make_dto()))

    @pytest.mark.asyncio
    async def test_inactive_user_raises(self, handler, mocks):
        mocks["user_repo"].get_by_id = AsyncMock(
            return_value=MagicMock(id=1, is_active=False)
        )

        with pytest.raises(UserNotFoundError):
            await handler.handle(CreatePositionCommand(make_dto()))
