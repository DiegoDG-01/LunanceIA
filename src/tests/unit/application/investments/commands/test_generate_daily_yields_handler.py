"""Unit tests for GenerateDailyYieldHandler (position-based engine)."""

import pytest
from dataclasses import replace
from unittest.mock import MagicMock, AsyncMock
from datetime import date, timedelta
from decimal import Decimal

from application.investments.commands.generate_daily_yields import (
    GenerateDailyYieldCommand,
    GenerateDailyYieldHandler,
)
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import InterestType, PositionType
from domain.objects.money import Money
from shared.utils.date import get_year_day_basis

TARGET_DATE = date(2026, 2, 27)


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
    def _build(self, positions):
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

        handler = GenerateDailyYieldHandler(position_repo, yield_repo, uow)
        return handler, position_repo, yield_repo, uow

    @pytest.mark.asyncio
    async def test_on_demand_compound_capitalizes_into_balance(self):
        position = make_position()
        handler, position_repo, yield_repo, uow = self._build([position])
        expected = expected_compound_yield(Decimal("10000.00"), Decimal("10.00"))

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 1, "skipped": 0, "errors": 0}
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

        assert stats == {"processed": 0, "skipped": 1, "errors": 0}
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

        assert stats == {"processed": 0, "skipped": 1, "errors": 0}
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

        assert stats == {"processed": 1, "skipped": 0, "errors": 0}

    @pytest.mark.asyncio
    async def test_zero_yield_is_skipped(self):
        position = make_position(annual_rate=Decimal("0.00"))
        handler, position_repo, yield_repo, _ = self._build([position])

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 0, "skipped": 1, "errors": 0}
        yield_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_error_in_one_position_does_not_stop_others(self):
        failing = make_position()
        healthy = replace(make_position(), id=6, uuid="pos-2")
        handler, position_repo, yield_repo, uow = self._build([failing, healthy])
        yield_repo.create = AsyncMock(side_effect=[Exception("db error"), MagicMock()])

        stats = await handler.handle(GenerateDailyYieldCommand(TARGET_DATE))

        assert stats == {"processed": 1, "skipped": 0, "errors": 1}
        uow.commit.assert_awaited_once()
