"""Unit tests for GetInvestmentProjectionsHandler (position-aggregate version)."""

import pytest
from dataclasses import replace
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from application.investments.queries.get_investment_projections import (
    GetInvestmentProjectionsQuery,
    GetInvestmentProjectionsHandler,
)
from domain.entities.account import Account
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import AccountType, PositionType
from domain.objects.money import Money
from shared.exceptions.domain import AccountNotFoundError


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
        "initial_balance": Money(Decimal("10000.00")),
        "annual_rate": Decimal("10.00"),
        "start_date": date.today() - timedelta(days=30),
    }
    defaults.update(overrides)
    position = InvestmentPosition.create_new(**defaults)
    return replace(position, id=pid, uuid=f"pos-{pid}")


def build_handler(account, positions):
    account_repo = MagicMock()
    account_repo.get_by_uuid_and_user_id = AsyncMock(return_value=account)
    position_repo = MagicMock()
    position_repo.get_by_account_id = AsyncMock(return_value=positions)
    return GetInvestmentProjectionsHandler(account_repo, position_repo)


@pytest.mark.unit
class TestGetInvestmentProjectionsHandler:
    @pytest.mark.asyncio
    async def test_account_not_found_raises(self):
        handler = build_handler(None, [])
        handler.account_repository.get_by_uuid_and_user_id = AsyncMock(
            return_value=None
        )

        with pytest.raises(AccountNotFoundError):
            await handler.handle(
                GetInvestmentProjectionsQuery(account_uuid="fake", user_id=1)
            )

    @pytest.mark.asyncio
    async def test_single_position_fills_rate_and_projects_365_days(self):
        position = make_position()
        handler = build_handler(make_account(), [position])

        result = await handler.handle(
            GetInvestmentProjectionsQuery(account_uuid="acc-1", user_id=1)
        )

        assert result.current_balance == Decimal("10000.00")
        assert result.annual_rate == Decimal("10.00")
        assert len(result.daily_projections) == 365
        assert result.projected_final_balance > Decimal("10000.00")

    @pytest.mark.asyncio
    async def test_multiple_positions_aggregate_balances(self):
        a = make_position(pid=1)
        b = make_position(pid=2, initial_balance=Money(Decimal("5000.00")))
        handler = build_handler(make_account(), [a, b])

        result = await handler.handle(
            GetInvestmentProjectionsQuery(
                account_uuid="acc-1", user_id=1, project_days=30
            )
        )

        assert result.current_balance == Decimal("15000.00")
        assert result.annual_rate is None
        assert result.interest_type is None
        assert len(result.daily_projections) == 30
        assert result.daily_projections[0].projected_balance > Decimal("15000.00")

    @pytest.mark.asyncio
    async def test_matured_fixed_term_contributes_flat_value(self):
        on_demand = make_position(pid=1)
        fixed = make_position(
            pid=2,
            position_type=PositionType.FIXED_TERM,
            term_days=40,
            start_date=date.today() - timedelta(days=30),  # vence en 10 días
            initial_balance=Money(Decimal("5000.00")),
        )
        handler = build_handler(make_account(), [on_demand, fixed])

        result = await handler.handle(
            GetInvestmentProjectionsQuery(
                account_uuid="acc-1", user_id=1, project_days=30
            )
        )

        assert len(result.daily_projections) == 30
        # Después del vencimiento del plazo (día 10), solo crece el a la vista:
        # el incremento diario del agregado baja tras el día 10.
        deltas = [
            result.daily_projections[i + 1].projected_balance
            - result.daily_projections[i].projected_balance
            for i in range(29)
        ]
        assert deltas[5] > deltas[15]

    @pytest.mark.asyncio
    async def test_liquidated_positions_are_excluded(self):
        active = make_position(pid=1)
        liquidated = make_position(pid=2)
        liquidated.liquidate(date.today())
        handler = build_handler(make_account(), [active, liquidated])

        result = await handler.handle(
            GetInvestmentProjectionsQuery(
                account_uuid="acc-1", user_id=1, project_days=10
            )
        )

        assert result.current_balance == Decimal("10000.00")
        assert result.annual_rate == Decimal("10.00")

    @pytest.mark.asyncio
    async def test_no_active_positions_returns_empty_projection(self):
        handler = build_handler(make_account(), [])

        result = await handler.handle(
            GetInvestmentProjectionsQuery(account_uuid="acc-1", user_id=1)
        )

        assert result.current_balance == Decimal(0)
        assert result.projected_final_balance == Decimal(0)
        assert result.daily_projections == []
