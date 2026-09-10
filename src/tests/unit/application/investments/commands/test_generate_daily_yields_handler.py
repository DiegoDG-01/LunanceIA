"""Unit tests for GenerateDailyYieldHandler (position-based engine)."""

import pytest
from dataclasses import replace
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from application.investments.commands.generate_daily_yields import (
    GenerateDailyYieldCommand,
    GenerateDailyYieldHandler,
)
from application.investments.services.position_overflow import PositionOverflowService
from domain.entities.account import Account
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import AccountType, InterestType, OverflowAction, PositionType
from domain.objects.money import Money
from shared.utils.date import get_year_day_basis

TARGET_DATE = date(2026, 2, 27)


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
        "name": "Cajita",
        "position_type": PositionType.ON_DEMAND,
        "initial_balance": Money(Decimal("10000.00")),
        "annual_rate": Decimal("10.00"),
        "start_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    position = InvestmentPosition.create_new(**defaults)
    return replace(position, id=5, uuid="pos-1")


def expected_compound_yield(principal: Decimal, rate: Decimal) -> Decimal:
    year_basis = Decimal(get_year_day_basis(TARGET_DATE))
    daily_rate = (1 + rate / Decimal(100)) ** (Decimal(1) / year_basis) - Decimal(1)
    return (principal * daily_rate).quantize(Decimal("0.01"))


def expected_simple_yield(principal: Decimal, rate: Decimal) -> Decimal:
    year_basis = Decimal(get_year_day_basis(TARGET_DATE))
    return (principal * (rate / Decimal(100) / year_basis)).quantize(Decimal("0.01"))


@pytest.mark.unit
class TestGenerateDailyYieldHandler:
    def _build(self, positions, account=None):
        uow = MagicMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()

        position_repo = MagicMock()
        position_repo.get_active_positions = AsyncMock(return_value=positions)
        by_id = {p.id: p for p in positions}
        position_repo.get_by_id = AsyncMock(
            side_effect=lambda position_id, for_update=False: by_id.get(position_id)
        )
        position_repo.update = AsyncMock(side_effect=lambda p: p)

        yield_repo = MagicMock()
        yield_repo.get_by_position_and_date = AsyncMock(return_value=None)
        yield_repo.create = AsyncMock(side_effect=lambda r: r)

        account_repo = MagicMock()
        account_repo.get_by_id = AsyncMock(return_value=account or make_account())
        account_repo.update = AsyncMock()

        transaction_repo = MagicMock()
        transaction_repo.create = AsyncMock(side_effect=lambda t: t)

        handler = GenerateDailyYieldHandler(
            position_repository=position_repo,
            investment_yield_repository=yield_repo,
            account_repository=account_repo,
            transaction_repository=transaction_repo,
            overflow_service=PositionOverflowService(position_repository=position_repo),
            uow=uow,
        )
        self.account_repo = account_repo
        self.transaction_repo = transaction_repo
        return handler, position_repo, yield_repo, uow

    @pytest.mark.asyncio
    async def test_on_demand_compound_capitalizes_into_balance(self):
        position = make_position()
        handler, position_repo, yield_repo, uow = self._build([position])
        expected = expected_compound_yield(Decimal("10000.00"), Decimal("10.00"))

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 1, "skipped": 0, "overflowed": 0, "errors": 0}
        assert position.balance.amount == Decimal("10000.00") + expected
        assert position.accrued_yield.amount == Decimal(0)

        record = yield_repo.create.call_args.args[0]
        assert record.position_id == 5
        assert record.account_id == 1
        assert record.yield_amount == expected
        assert record.cumulative_balance == position.balance.amount
        uow.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fixed_term_accrues_apart_and_compounds_over_total(self):
        position = make_position(position_type=PositionType.FIXED_TERM, term_days=365)
        position.accrued_yield = Money(Decimal("100.00"))
        handler, _, yield_repo, _ = self._build([position])
        expected = expected_compound_yield(Decimal("10100.00"), Decimal("10.00"))

        await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert position.balance.amount == Decimal("10000.00")
        assert position.accrued_yield.amount == Decimal("100.00") + expected

        record = yield_repo.create.call_args.args[0]
        assert record.principal_amount == Decimal("10100.00")

    @pytest.mark.asyncio
    async def test_simple_interest_uses_base_principal(self):
        position = make_position(interest_type=InterestType.SIMPLE)
        position.accrue_yield(Money(Decimal("500.00")))  # capital base sigue en 10000
        handler, _, yield_repo, _ = self._build([position])
        expected = expected_simple_yield(Decimal("10000.00"), Decimal("10.00"))

        await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        record = yield_repo.create.call_args.args[0]
        assert record.principal_amount == Decimal("10000.00")
        assert record.yield_amount == expected

    @pytest.mark.asyncio
    async def test_existing_yield_for_date_is_skipped(self):
        position = make_position()
        handler, position_repo, yield_repo, _ = self._build([position])
        yield_repo.get_by_position_and_date = AsyncMock(return_value=MagicMock())

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 0, "skipped": 1, "overflowed": 0, "errors": 0}
        position_repo.update.assert_not_awaited()
        yield_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_matured_fixed_term_is_skipped(self):
        position = make_position(
            position_type=PositionType.FIXED_TERM,
            term_days=30,
            start_date=TARGET_DATE - timedelta(days=60),
        )
        handler, _, yield_repo, _ = self._build([position])

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 0, "skipped": 1, "overflowed": 0, "errors": 0}
        yield_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_yields_on_maturity_date_itself(self):
        position = make_position(
            position_type=PositionType.FIXED_TERM,
            term_days=30,
            start_date=TARGET_DATE - timedelta(days=30),
        )
        handler, _, yield_repo, _ = self._build([position])

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 1, "skipped": 0, "overflowed": 0, "errors": 0}

    @pytest.mark.asyncio
    async def test_zero_yield_is_skipped(self):
        position = make_position(annual_rate=Decimal("0.00"))
        handler, position_repo, yield_repo, _ = self._build([position])

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 0, "skipped": 1, "overflowed": 0, "errors": 0}
        yield_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_error_in_one_position_does_not_stop_others(self):
        failing = make_position()
        healthy = replace(make_position(), id=6, uuid="pos-2")
        handler, position_repo, yield_repo, uow = self._build([failing, healthy])
        yield_repo.create = AsyncMock(side_effect=[Exception("db error"), MagicMock()])

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 1, "skipped": 0, "overflowed": 0, "errors": 1}
        uow.commit.assert_awaited_once()


@pytest.mark.unit
class TestDailyYieldOverflow:
    """Test a capped position that keeps earning past its cap."""

    def _build(self, positions, account=None):
        return TestGenerateDailyYieldHandler._build(self, positions, account)

    @pytest.mark.asyncio
    async def test_full_position_sends_the_whole_yield_to_available(self):
        position = make_position(max_balance=Decimal("10000.00"))
        account = make_account("500.00")
        handler, _, yield_repo, _ = self._build([position], account)
        expected = expected_compound_yield(Decimal("10000.00"), Decimal("10.00"))

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats["overflowed"] == 1
        # El tope no se rebasa ni un día.
        assert position.balance.amount == Decimal("10000.00")
        assert account.current_balance.amount == Decimal("500.00") + expected

        movement = self.transaction_repo.create.call_args.args[0]
        assert movement.amount.amount == expected
        assert movement.position_id == 5
        # El histórico guarda lo que ganó, no lo que le quedó.
        assert yield_repo.create.call_args.args[0].yield_amount == expected

    @pytest.mark.asyncio
    async def test_yield_below_the_cap_creates_no_transaction(self):
        position = make_position(max_balance=Decimal("50000.00"))
        account = make_account("500.00")
        handler, _, _, _ = self._build([position], account)

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats["overflowed"] == 0
        assert account.current_balance.amount == Decimal("500.00")
        self.transaction_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_chain_absorbs_the_yield_without_a_transaction(self):
        target = replace(make_position(), id=6, uuid="pos-2")
        position = make_position(
            max_balance=Decimal("10000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=6,
        )
        account = make_account("500.00")
        handler, _, _, _ = self._build([position, target], account)
        expected = expected_compound_yield(Decimal("10000.00"), Decimal("10.00"))

        await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert position.balance.amount == Decimal("10000.00")
        # El excedente entró al siguiente apartado sin cruzar el disponible.
        assert target.balance.amount > Decimal("10000.00") + expected
        assert account.current_balance.amount == Decimal("500.00")
        self.transaction_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_account_counts_as_an_error(self):
        position = make_position(max_balance=Decimal("10000.00"))
        handler, _, yield_repo, _ = self._build([position])
        self.account_repo.get_by_id = AsyncMock(return_value=None)

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 0, "skipped": 0, "overflowed": 0, "errors": 1}
        yield_repo.create.assert_not_awaited()
