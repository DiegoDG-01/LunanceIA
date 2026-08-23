"""Unit tests for ProcessMaturedPositionsHandler."""

import pytest
from dataclasses import replace
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from application.investments.commands.process_matured_positions import (
    ProcessMaturedPositionsCommand,
    ProcessMaturedPositionsHandler,
)
from domain.entities.account import Account
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import (
    AccountType,
    MaturityAction,
    PositionStatus,
    PositionType,
)
from domain.objects.money import Money

TARGET_DATE = date(2026, 4, 1)


def make_account(balance: str = "500.00") -> Account:
    return Account(
        id=1,
        uuid="acc-1",
        user_id=7,
        bank_id=1,
        name="Cuenta SOFIPO",
        account_type=AccountType.SAVINGS,
        current_balance=Money(Decimal(balance)),
        is_active=True,
        creation_date=datetime.now(timezone.utc),
    )


def make_due_position(on_maturity: MaturityAction, **overrides) -> InvestmentPosition:
    defaults = {
        "account_id": 1,
        "name": "Plazo 90",
        "position_type": PositionType.FIXED_TERM,
        "initial_balance": Money(Decimal("1000.00")),
        "annual_rate": Decimal("10.00"),
        "start_date": TARGET_DATE - timedelta(days=90),
        "term_days": 90,
        "on_maturity": on_maturity,
    }
    defaults.update(overrides)
    position = InvestmentPosition.create_new(**defaults)
    position.accrue_yield(Money(Decimal("25.00")))
    return replace(position, id=5, uuid="pos-1")


def build_mocks(account, positions):
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()

    account_repo = MagicMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    account_repo.update = AsyncMock()

    position_repo = MagicMock()
    position_repo.get_due_for_maturity = AsyncMock(return_value=positions)
    by_id = {p.id: p for p in positions}
    position_repo.get_by_id = AsyncMock(
        side_effect=lambda position_id, for_update=False: by_id.get(position_id)
    )
    position_repo.update = AsyncMock(side_effect=lambda p: p)

    transaction_repo = MagicMock()
    transaction_repo.create = AsyncMock(side_effect=lambda t: t)

    notification_repo = MagicMock()
    notification_repo.create = AsyncMock()

    handler = ProcessMaturedPositionsHandler(
        position_repository=position_repo,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        notification_repository=notification_repo,
        uow=uow,
    )
    return handler, {
        "account_repo": account_repo,
        "position_repo": position_repo,
        "transaction_repo": transaction_repo,
        "notification_repo": notification_repo,
        "uow": uow,
    }


@pytest.mark.unit
class TestProcessMaturedPositionsHandler:
    @pytest.mark.asyncio
    async def test_auto_renew_reinvests_for_same_term(self):
        account = make_account()
        position = make_due_position(MaturityAction.AUTO_RENEW)
        handler, mocks = build_mocks(account, [position])

        stats = await handler.handle(ProcessMaturedPositionsCommand(TARGET_DATE))

        assert stats == {"renewed": 1, "liquidated": 0, "held": 0, "errors": 0}
        assert position.status == PositionStatus.ACTIVE
        assert position.balance.amount == Decimal("1025.00")
        assert position.accrued_yield.amount == Decimal(0)
        assert position.maturity_date == TARGET_DATE + timedelta(days=90)
        # El dinero no toca el saldo disponible
        assert account.current_balance.amount == Decimal("500.00")
        mocks["transaction_repo"].create.assert_not_awaited()
        mocks["notification_repo"].create.assert_awaited_once()
        mocks["uow"].commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_liquidate_credits_available_balance(self):
        account = make_account("500.00")
        position = make_due_position(MaturityAction.LIQUIDATE)
        handler, mocks = build_mocks(account, [position])

        stats = await handler.handle(ProcessMaturedPositionsCommand(TARGET_DATE))

        assert stats == {"renewed": 0, "liquidated": 1, "held": 0, "errors": 0}
        assert position.status == PositionStatus.LIQUIDATED
        # Vencido: capital + rendimiento completos, sin penalización
        assert account.current_balance.amount == Decimal("1525.00")

        movement = mocks["transaction_repo"].create.call_args.args[0]
        assert movement.amount.amount == Decimal("1025.00")
        assert movement.position_id == 5
        mocks["notification_repo"].create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_hold_marks_matured_and_notifies(self):
        account = make_account()
        position = make_due_position(MaturityAction.HOLD)
        handler, mocks = build_mocks(account, [position])

        stats = await handler.handle(ProcessMaturedPositionsCommand(TARGET_DATE))

        assert stats == {"renewed": 0, "liquidated": 0, "held": 1, "errors": 0}
        assert position.status == PositionStatus.MATURED
        assert position.total_value.amount == Decimal("1025.00")
        assert account.current_balance.amount == Decimal("500.00")
        mocks["transaction_repo"].create.assert_not_awaited()
        mocks["notification_repo"].create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_position_no_longer_due_under_lock_is_ignored(self):
        account = make_account()
        preview = make_due_position(MaturityAction.LIQUIDATE)
        fresh = replace(preview)
        fresh.renew(TARGET_DATE)  # Otro proceso ya lo renovó
        handler, mocks = build_mocks(account, [preview])
        mocks["position_repo"].get_by_id = AsyncMock(return_value=fresh)

        stats = await handler.handle(ProcessMaturedPositionsCommand(TARGET_DATE))

        assert stats == {"renewed": 0, "liquidated": 0, "held": 0, "errors": 0}
        mocks["transaction_repo"].create.assert_not_awaited()
        mocks["notification_repo"].create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_error_in_one_position_does_not_stop_others(self):
        account = make_account()
        failing = make_due_position(MaturityAction.LIQUIDATE)
        healthy = replace(make_due_position(MaturityAction.HOLD), id=6, uuid="pos-2")
        handler, mocks = build_mocks(account, [failing, healthy])
        mocks["transaction_repo"].create = AsyncMock(side_effect=Exception("db error"))

        stats = await handler.handle(ProcessMaturedPositionsCommand(TARGET_DATE))

        assert stats["errors"] == 1
        assert stats["held"] == 1
        mocks["uow"].commit.assert_awaited_once()
