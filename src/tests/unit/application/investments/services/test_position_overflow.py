"""Unit tests for PositionOverflowService: the chain that spills excess money."""

import pytest
from dataclasses import replace
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from application.investments.services.position_overflow import (
    MAX_OVERFLOW_HOPS,
    PositionOverflowService,
)
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import OverflowAction, PositionType
from domain.objects.money import Money
from shared.exceptions.domain import InvalidOverflowTargetError


def make_position(position_id: int, **overrides) -> InvestmentPosition:
    defaults = {
        "account_id": 1,
        "name": f"Apartado {position_id}",
        "position_type": PositionType.ON_DEMAND,
        "initial_balance": Money(Decimal("1000.00")),
        "annual_rate": Decimal("10.00"),
        "start_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    position = InvestmentPosition.create_new(**defaults)
    return replace(position, id=position_id, uuid=f"pos-{position_id}")


def build_service(*positions: InvestmentPosition):
    """Wire a repository that resolves the given positions by id."""
    by_id = {position.id: position for position in positions}

    repo = MagicMock()
    repo.get_by_id = AsyncMock(
        side_effect=lambda position_id, **_: by_id.get(position_id)
    )
    repo.update = AsyncMock()
    return PositionOverflowService(position_repository=repo), repo


@pytest.mark.unit
class TestSpillToAvailable:
    """Test the cases that end up in the account's available balance."""

    async def test_position_without_target_sends_everything_to_available(self):
        source = make_position(1, max_balance=Decimal("1000.00"))
        service, repo = build_service(source)

        to_available = await service.spill(source, Money(Decimal("6.85")))

        assert to_available.amount == Decimal("6.85")
        repo.update.assert_not_called()

    async def test_zero_amount_short_circuits(self):
        source = make_position(1)
        service, repo = build_service(source)

        to_available = await service.spill(source, Money(Decimal("0.00")))

        assert to_available.amount == Decimal(0)
        repo.get_by_id.assert_not_called()

    async def test_liquidated_target_falls_back_to_available(self):
        target = make_position(2)
        target.liquidate(date(2026, 2, 1))
        source = make_position(
            1,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=2,
        )
        service, repo = build_service(source, target)

        to_available = await service.spill(source, Money(Decimal("6.85")))

        assert to_available.amount == Decimal("6.85")
        repo.update.assert_not_called()

    async def test_missing_target_falls_back_to_available(self):
        source = make_position(
            1,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=99,
        )
        service, _ = build_service(source)

        to_available = await service.spill(source, Money(Decimal("6.85")))

        assert to_available.amount == Decimal("6.85")

    async def test_cycle_in_database_does_not_hang(self):
        source = make_position(
            1,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=2,
        )
        target = make_position(
            2,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=1,
        )
        service, _ = build_service(source, target)

        to_available = await service.spill(source, Money(Decimal("6.85")))

        assert to_available.amount == Decimal("6.85")

    async def test_chain_longer_than_the_hop_limit_bails_out(self):
        chain = []
        total = MAX_OVERFLOW_HOPS + 3
        for position_id in range(1, total + 1):
            chain.append(
                make_position(
                    position_id,
                    max_balance=Decimal("1000.00"),
                    overflow_action=OverflowAction.TO_POSITION,
                    overflow_position_id=position_id + 1,
                )
            )
        service, _ = build_service(*chain)

        to_available = await service.spill(chain[0], Money(Decimal("6.85")))

        assert to_available.amount == Decimal("6.85")


@pytest.mark.unit
class TestSpillThroughTheChain:
    """Test money actually landing in the next positions."""

    async def test_target_with_room_absorbs_everything(self):
        target = make_position(2, max_balance=Decimal("5000.00"))
        source = make_position(
            1,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=2,
        )
        service, repo = build_service(source, target)

        to_available = await service.spill(source, Money(Decimal("6.85")))

        assert to_available.amount == Decimal(0)
        assert target.balance.amount == Decimal("1006.85")
        repo.update.assert_awaited_once()

    async def test_uncapped_target_absorbs_everything(self):
        target = make_position(2)
        source = make_position(
            1,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=2,
        )
        service, _ = build_service(source, target)

        to_available = await service.spill(source, Money(Decimal("500.00")))

        assert to_available.amount == Decimal(0)
        assert target.balance.amount == Decimal("1500.00")

    async def test_full_target_passes_the_money_along(self):
        last = make_position(3)
        middle = make_position(
            2,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=3,
        )
        source = make_position(
            1,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=2,
        )
        service, _ = build_service(source, middle, last)

        to_available = await service.spill(source, Money(Decimal("300.00")))

        assert to_available.amount == Decimal(0)
        assert middle.balance.amount == Decimal("1000.00")
        assert last.balance.amount == Decimal("1300.00")

    async def test_chain_splits_the_money_and_returns_the_leftover(self):
        middle = make_position(2, max_balance=Decimal("1100.00"))
        source = make_position(
            1,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=2,
        )
        service, _ = build_service(source, middle)

        to_available = await service.spill(source, Money(Decimal("300.00")))

        assert middle.balance.amount == Decimal("1100.00")
        assert to_available.amount == Decimal("200.00")

    async def test_simple_interest_target_grows_its_base(self):
        from domain.objects.enums import InterestType

        target = make_position(2, interest_type=InterestType.SIMPLE)
        source = make_position(
            1,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=2,
        )
        service, _ = build_service(source, target)

        await service.spill(source, Money(Decimal("500.00")))

        assert target.base_principal == Decimal("1500.00")


@pytest.mark.unit
class TestValidateTarget:
    """Test the checks that only the database can answer."""

    async def test_valid_target_passes(self):
        target = make_position(2)
        source = make_position(1)
        service, _ = build_service(source, target)

        await service.validate_target(source, 2)

    async def test_missing_target_raises(self):
        source = make_position(1)
        service, _ = build_service(source)

        with pytest.raises(InvalidOverflowTargetError):
            await service.validate_target(source, 99)

    async def test_target_from_another_account_raises(self):
        target = replace(make_position(2), account_id=2)
        source = make_position(1)
        service, _ = build_service(source, target)

        with pytest.raises(InvalidOverflowTargetError):
            await service.validate_target(source, 2)

    async def test_fixed_term_target_raises(self):
        target = make_position(2, position_type=PositionType.FIXED_TERM, term_days=90)
        source = make_position(1)
        service, _ = build_service(source, target)

        with pytest.raises(InvalidOverflowTargetError):
            await service.validate_target(source, 2)

    async def test_liquidated_target_raises(self):
        target = make_position(2)
        target.liquidate(date(2026, 2, 1))
        source = make_position(1)
        service, _ = build_service(source, target)

        with pytest.raises(InvalidOverflowTargetError):
            await service.validate_target(source, 2)

    async def test_target_that_loops_back_raises(self):
        target = make_position(
            2,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=1,
        )
        source = make_position(1)
        service, _ = build_service(source, target)

        with pytest.raises(InvalidOverflowTargetError):
            await service.validate_target(source, 2)

    async def test_indirect_loop_back_raises(self):
        middle = make_position(
            3,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=1,
        )
        target = make_position(
            2,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=3,
        )
        source = make_position(1)
        service, _ = build_service(source, target, middle)

        with pytest.raises(InvalidOverflowTargetError):
            await service.validate_target(source, 2)

    async def test_chain_that_ends_is_accepted(self):
        last = make_position(3)
        target = make_position(
            2,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=3,
        )
        source = make_position(1)
        service, _ = build_service(source, target, last)

        await service.validate_target(source, 2)

    async def test_new_position_can_point_at_an_existing_one(self):
        target = make_position(2)
        source = replace(make_position(1), id=None, uuid=None)
        service, _ = build_service(target)

        await service.validate_target(source, 2)
