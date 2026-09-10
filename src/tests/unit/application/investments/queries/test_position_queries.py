"""Unit tests for ListPositions and GetPositionProjections handlers."""

import pytest
from dataclasses import replace
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from application.investments.queries.list_positions import (
    ListPositionsQuery,
    ListPositionsHandler,
)
from application.investments.queries.get_position_projections import (
    GetPositionProjectionsQuery,
    GetPositionProjectionsHandler,
)
from domain.entities.account import Account
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import AccountType, PositionType
from domain.objects.money import Money
from shared.exceptions.domain import (
    AccountNotFoundError,
    InvestmentPositionNotFoundError,
)


def make_account() -> Account:
    return Account(
        id=10,
        uuid="acc-1",
        user_id=1,
        name="Cuenta SOFIPO",
        account_type=AccountType.SAVINGS,
        current_balance=Money(Decimal("500.00")),
        bank_id=1,
        is_active=True,
        creation_date=datetime.now(timezone.utc),
    )


def make_position(pid: int = 5, **overrides) -> InvestmentPosition:
    defaults = {
        "account_id": 10,
        "name": "Cajita",
        "position_type": PositionType.ON_DEMAND,
        "initial_balance": Money(Decimal("1000.00")),
        "annual_rate": Decimal("10.00"),
        "start_date": date.today() - timedelta(days=30),
    }
    defaults.update(overrides)
    position = InvestmentPosition.create_new(**defaults)
    return replace(position, id=pid, uuid=f"pos-{pid}")


@pytest.mark.unit
class TestListPositionsHandler:
    def _build(self, account, positions):
        account_repo = MagicMock()
        account_repo.get_by_uuid_and_user_id = AsyncMock(return_value=account)
        position_repo = MagicMock()
        position_repo.get_by_account_id = AsyncMock(return_value=positions)
        return ListPositionsHandler(account_repo, position_repo)

    @pytest.mark.asyncio
    async def test_returns_totals_and_positions(self):
        a = make_position(pid=1)
        b = make_position(pid=2, initial_balance=Money(Decimal("2500.00")))
        b.accrue_yield(Money(Decimal("10.00")))
        handler = self._build(make_account(), [a, b])

        result = await handler.handle(
            ListPositionsQuery(account_uuid="acc-1", user_id=1)
        )

        assert result.available_balance == Decimal("500.00")
        assert result.invested_balance == Decimal("3510.00")
        assert result.total_balance == Decimal("4010.00")
        assert len(result.positions) == 2
        assert result.positions[0].account_uuid == "acc-1"

    @pytest.mark.asyncio
    async def test_liquidated_positions_hidden_by_default(self):
        active = make_position(pid=1)
        liquidated = make_position(pid=2)
        liquidated.liquidate(date.today())
        handler = self._build(make_account(), [active, liquidated])

        result = await handler.handle(
            ListPositionsQuery(account_uuid="acc-1", user_id=1)
        )
        assert len(result.positions) == 1

        result_all = await handler.handle(
            ListPositionsQuery(account_uuid="acc-1", user_id=1, include_liquidated=True)
        )
        assert len(result_all.positions) == 2
        # El liquidado no cuenta en el total invertido
        assert result_all.invested_balance == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_account_not_found_raises(self):
        handler = self._build(None, [])

        with pytest.raises(AccountNotFoundError):
            await handler.handle(ListPositionsQuery(account_uuid="fake", user_id=1))


@pytest.mark.unit
class TestGetPositionProjectionsHandler:
    def _build(self, position):
        position_repo = MagicMock()
        position_repo.get_by_uuid_and_user_id = AsyncMock(return_value=position)
        return GetPositionProjectionsHandler(position_repo)

    @pytest.mark.asyncio
    async def test_position_not_found_raises(self):
        handler = self._build(None)

        with pytest.raises(InvestmentPositionNotFoundError):
            await handler.handle(
                GetPositionProjectionsQuery(position_uuid="fake", user_id=1)
            )

    @pytest.mark.asyncio
    async def test_on_demand_projects_365_days_by_default(self):
        handler = self._build(make_position())

        result = await handler.handle(
            GetPositionProjectionsQuery(position_uuid="pos-5", user_id=1)
        )

        assert len(result.daily_projections) == 365
        assert result.current_value == Decimal("1000.00")
        assert result.projected_final_balance > Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_fixed_term_caps_projection_at_maturity(self):
        position = make_position(
            position_type=PositionType.FIXED_TERM,
            term_days=40,
            start_date=date.today() - timedelta(days=30),  # vence en 10 días
        )
        handler = self._build(position)

        result = await handler.handle(
            GetPositionProjectionsQuery(
                position_uuid="pos-5", user_id=1, project_days=100
            )
        )

        assert len(result.daily_projections) == 10

    @pytest.mark.asyncio
    async def test_past_maturity_returns_flat_value(self):
        position = make_position(
            position_type=PositionType.FIXED_TERM,
            term_days=10,
            start_date=date.today() - timedelta(days=30),  # ya venció
        )
        position.accrue_yield(Money(Decimal("50.00")))
        handler = self._build(position)

        result = await handler.handle(
            GetPositionProjectionsQuery(position_uuid="pos-5", user_id=1)
        )

        assert result.daily_projections == []
        assert result.projected_final_balance == Decimal("1050.00")


@pytest.mark.unit
class TestProjectionsWithCap:
    """Test that a capped position projects a plateau, not endless growth."""

    def _build(self, position):
        position_repo = MagicMock()
        position_repo.get_by_uuid_and_user_id = AsyncMock(return_value=position)
        return GetPositionProjectionsHandler(position_repo)

    @pytest.mark.asyncio
    async def test_full_position_projects_a_flat_line(self):
        position = make_position(max_balance=Decimal("1000.00"))
        handler = self._build(position)

        result = await handler.handle(
            GetPositionProjectionsQuery(
                position_uuid="pos-5", user_id=1, project_days=30
            )
        )

        balances = {p.projected_balance for p in result.daily_projections}
        assert balances == {Decimal("1000.00")}
        assert result.projected_final_balance == Decimal("1000.00")
        assert result.max_balance == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_the_overflow_is_reported_day_by_day(self):
        position = make_position(max_balance=Decimal("1000.00"))
        handler = self._build(position)

        result = await handler.handle(
            GetPositionProjectionsQuery(
                position_uuid="pos-5", user_id=1, project_days=30
            )
        )

        # Lo que rinde cada día es exactamente lo que se desborda.
        assert all(
            p.overflow_amount == p.yield_amount for p in result.daily_projections
        )
        assert result.projected_overflow == sum(
            p.yield_amount for p in result.daily_projections
        )

    @pytest.mark.asyncio
    async def test_cap_above_balance_grows_until_it_hits_the_ceiling(self):
        position = make_position(max_balance=Decimal("1005.00"))
        handler = self._build(position)

        result = await handler.handle(
            GetPositionProjectionsQuery(
                position_uuid="pos-5", user_id=1, project_days=90
            )
        )

        assert result.daily_projections[0].overflow_amount == Decimal(0)
        assert result.projected_final_balance == Decimal("1005.00")
        assert result.projected_overflow > Decimal(0)

    @pytest.mark.asyncio
    async def test_position_without_cap_reports_no_overflow(self):
        handler = self._build(make_position())

        result = await handler.handle(
            GetPositionProjectionsQuery(
                position_uuid="pos-5", user_id=1, project_days=30
            )
        )

        assert result.projected_overflow == Decimal(0)
        assert result.max_balance is None
        assert result.projected_final_balance > Decimal("1000.00")
