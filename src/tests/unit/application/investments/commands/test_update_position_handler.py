"""Unit tests for the UpdatePosition handler (cap and overflow configuration)."""

import pytest
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from application.dto.investment_position_dto import UpdatePositionDTO
from application.investments.commands.update_position import (
    UpdatePositionCommand,
    UpdatePositionHandler,
)
from application.investments.services.position_overflow import PositionOverflowService
from domain.entities.account import Account
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import AccountType, OverflowAction, PositionType
from domain.objects.money import Money
from shared.exceptions.domain import (
    InvalidOverflowTargetError,
    InvalidPositionCapError,
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


def make_position(position_id: int = 5, **overrides) -> InvestmentPosition:
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


def build_handler(account, *positions):
    by_id = {position.id: position for position in positions}
    by_uuid = {position.uuid: position for position in positions}

    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()

    user_repo = MagicMock()
    user_repo.get_by_id = AsyncMock(return_value=MagicMock(id=1, is_active=True))

    account_repo = MagicMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    account_repo.update = AsyncMock()

    position_repo = MagicMock()
    position_repo.get_by_id = AsyncMock(
        side_effect=lambda position_id, **_: by_id.get(position_id)
    )
    position_repo.get_by_uuid_and_user_id = AsyncMock(
        side_effect=lambda position_uuid, user_id, **_: by_uuid.get(position_uuid)
    )
    position_repo.update = AsyncMock()

    transaction_repo = MagicMock()
    transaction_repo.create = AsyncMock()

    handler = UpdatePositionHandler(
        user_repository=user_repo,
        account_repository=account_repo,
        position_repository=position_repo,
        transaction_repository=transaction_repo,
        overflow_service=PositionOverflowService(position_repository=position_repo),
        uow=uow,
    )
    return handler, transaction_repo, account_repo


@pytest.mark.unit
class TestUpdatePositionName:
    """Test the plain rename path."""

    async def test_renames_without_touching_the_cap(self):
        position = make_position(max_balance=Decimal("2000.00"))
        handler, transaction_repo, _ = build_handler(make_account(), position)

        result = await handler.handle(
            UpdatePositionCommand(
                dto=UpdatePositionDTO(
                    user_id=1, position_uuid="pos-5", name="Ahorro 10%"
                )
            )
        )

        assert result.name == "Ahorro 10%"
        assert position.max_balance == Decimal("2000.00")
        transaction_repo.create.assert_not_called()

    async def test_unknown_position_raises(self):
        handler, _, _ = build_handler(make_account())

        with pytest.raises(InvestmentPositionNotFoundError):
            await handler.handle(
                UpdatePositionCommand(
                    dto=UpdatePositionDTO(user_id=1, position_uuid="pos-404")
                )
            )


@pytest.mark.unit
class TestUpdatePositionCap:
    """Test setting, lowering and removing the cap."""

    async def test_setting_a_cap_above_balance_moves_no_money(self):
        position = make_position()
        handler, transaction_repo, account_repo = build_handler(
            make_account(), position
        )

        result = await handler.handle(
            UpdatePositionCommand(
                dto=UpdatePositionDTO(
                    user_id=1,
                    position_uuid="pos-5",
                    cap_provided=True,
                    max_balance=Decimal("5000.00"),
                )
            )
        )

        assert result.max_balance == Decimal("5000.00")
        assert result.overflow_action == OverflowAction.TO_AVAILABLE
        transaction_repo.create.assert_not_called()
        account_repo.update.assert_not_called()

    async def test_lowering_the_cap_sends_the_excess_to_available_now(self):
        position = make_position()
        account = make_account("500.00")
        handler, transaction_repo, account_repo = build_handler(account, position)

        result = await handler.handle(
            UpdatePositionCommand(
                dto=UpdatePositionDTO(
                    user_id=1,
                    position_uuid="pos-5",
                    cap_provided=True,
                    max_balance=Decimal("800.00"),
                )
            )
        )

        assert position.balance.amount == Decimal("800.00")
        assert account.current_balance.amount == Decimal("700.00")
        assert result.account_available_balance == Decimal("700.00")
        transaction_repo.create.assert_awaited_once()
        account_repo.update.assert_awaited_once()

    async def test_lowering_the_cap_sends_the_excess_down_the_chain(self):
        target = make_position(6)
        position = make_position(5)
        account = make_account("500.00")
        handler, transaction_repo, _ = build_handler(account, position, target)

        await handler.handle(
            UpdatePositionCommand(
                dto=UpdatePositionDTO(
                    user_id=1,
                    position_uuid="pos-5",
                    cap_provided=True,
                    max_balance=Decimal("800.00"),
                    overflow_action=OverflowAction.TO_POSITION,
                    overflow_position_uuid="pos-6",
                )
            )
        )

        assert position.balance.amount == Decimal("800.00")
        assert target.balance.amount == Decimal("1200.00")
        # El dinero nunca cruzó al disponible, así que no hay transacción.
        assert account.current_balance.amount == Decimal("500.00")
        transaction_repo.create.assert_not_called()

    async def test_chain_leftover_still_reaches_available(self):
        target = make_position(6, max_balance=Decimal("1100.00"))
        position = make_position(5)
        account = make_account("500.00")
        handler, transaction_repo, _ = build_handler(account, position, target)

        await handler.handle(
            UpdatePositionCommand(
                dto=UpdatePositionDTO(
                    user_id=1,
                    position_uuid="pos-5",
                    cap_provided=True,
                    max_balance=Decimal("700.00"),
                    overflow_action=OverflowAction.TO_POSITION,
                    overflow_position_uuid="pos-6",
                )
            )
        )

        assert target.balance.amount == Decimal("1100.00")
        assert account.current_balance.amount == Decimal("700.00")
        transaction_repo.create.assert_awaited_once()

    async def test_removing_the_cap_clears_the_overflow_config(self):
        target = make_position(6)
        position = make_position(
            5,
            max_balance=Decimal("2000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=6,
        )
        handler, _, _ = build_handler(make_account(), position, target)

        result = await handler.handle(
            UpdatePositionCommand(
                dto=UpdatePositionDTO(
                    user_id=1, position_uuid="pos-5", cap_provided=True
                )
            )
        )

        assert result.max_balance is None
        assert result.overflow_action is None
        assert result.overflow_position_uuid is None

    async def test_response_exposes_the_target_uuid_not_its_id(self):
        target = make_position(6)
        position = make_position(5)
        handler, _, _ = build_handler(make_account(), position, target)

        result = await handler.handle(
            UpdatePositionCommand(
                dto=UpdatePositionDTO(
                    user_id=1,
                    position_uuid="pos-5",
                    cap_provided=True,
                    max_balance=Decimal("5000.00"),
                    overflow_action=OverflowAction.TO_POSITION,
                    overflow_position_uuid="pos-6",
                )
            )
        )

        assert result.overflow_position_uuid == "pos-6"


@pytest.mark.unit
class TestUpdatePositionValidation:
    """Test the configurations that must be rejected."""

    async def test_to_position_without_target_raises(self):
        position = make_position()
        handler, _, _ = build_handler(make_account(), position)

        with pytest.raises(InvalidOverflowTargetError):
            await handler.handle(
                UpdatePositionCommand(
                    dto=UpdatePositionDTO(
                        user_id=1,
                        position_uuid="pos-5",
                        cap_provided=True,
                        max_balance=Decimal("5000.00"),
                        overflow_action=OverflowAction.TO_POSITION,
                    )
                )
            )

    async def test_unknown_target_raises(self):
        position = make_position()
        handler, _, _ = build_handler(make_account(), position)

        with pytest.raises(InvalidOverflowTargetError):
            await handler.handle(
                UpdatePositionCommand(
                    dto=UpdatePositionDTO(
                        user_id=1,
                        position_uuid="pos-5",
                        cap_provided=True,
                        max_balance=Decimal("5000.00"),
                        overflow_action=OverflowAction.TO_POSITION,
                        overflow_position_uuid="pos-404",
                    )
                )
            )

    async def test_target_that_closes_a_cycle_raises(self):
        target = make_position(
            6,
            max_balance=Decimal("1000.00"),
            overflow_action=OverflowAction.TO_POSITION,
            overflow_position_id=5,
        )
        position = make_position(5)
        handler, _, _ = build_handler(make_account(), position, target)

        with pytest.raises(InvalidOverflowTargetError):
            await handler.handle(
                UpdatePositionCommand(
                    dto=UpdatePositionDTO(
                        user_id=1,
                        position_uuid="pos-5",
                        cap_provided=True,
                        max_balance=Decimal("5000.00"),
                        overflow_action=OverflowAction.TO_POSITION,
                        overflow_position_uuid="pos-6",
                    )
                )
            )

    async def test_overflow_action_without_cap_raises(self):
        position = make_position()
        handler, _, _ = build_handler(make_account(), position)

        with pytest.raises(InvalidPositionCapError):
            await handler.handle(
                UpdatePositionCommand(
                    dto=UpdatePositionDTO(
                        user_id=1,
                        position_uuid="pos-5",
                        cap_provided=True,
                        overflow_action=OverflowAction.TO_AVAILABLE,
                    )
                )
            )
