import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone

from application.accounts.commands.state_account import (
    StateAccountCommand,
    StateAccountHandler,
)
from domain.entities.account import Account
from domain.entities.bank import Bank
from domain.objects.enums import AccountType
from domain.objects.money import Money
from domain.services.account_service import AccountService
from shared.exceptions.domain import AccountNotFoundError


@pytest.mark.unit
class TestStateAccountHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "account_repo": MagicMock(),
            "account_service": MagicMock(spec=AccountService),
            "bank_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return StateAccountHandler(
            account_repository=mocks["account_repo"],
            account_service=mocks["account_service"],
            bank_repository=mocks["bank_repo"],
            uow=mocks["uow"],
        )

    def _make_account(self, is_active: bool = True) -> Account:
        return Account(
            id=10,
            uuid="acc-uuid-1",
            user_id=1,
            bank_id=1,
            name="Test Account",
            account_type=AccountType.SAVINGS,
            current_balance=Money(Decimal("1000.00")),
            is_active=is_active,
            creation_date=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_toggle_active_to_inactive(self, handler, mocks):
        active_account = self._make_account(is_active=True)
        toggled_account = self._make_account(is_active=False)
        toggled_account.bank_name = None
        toggled_account.bank_code = None

        mock_bank = Bank(id=1, name="BBVA", code="BBV", country="MX")

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=active_account
        )
        mocks["account_repo"].switch_status = AsyncMock(return_value=toggled_account)
        mocks["bank_repo"].get_by_id = AsyncMock(return_value=mock_bank)

        command = StateAccountCommand(account_uuid="acc-uuid-1", user_id=1)
        result = await handler.handle(command)

        assert result.is_active is False
        assert result.bank_name == "BBVA"
        assert result.bank_code == "BBV"
        mocks["account_repo"].switch_status.assert_called_once_with(active_account)

    @pytest.mark.asyncio
    async def test_toggle_inactive_to_active(self, handler, mocks):
        inactive_account = self._make_account(is_active=False)
        toggled_account = self._make_account(is_active=True)
        toggled_account.bank_name = None
        toggled_account.bank_code = None

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=inactive_account
        )
        mocks["account_repo"].switch_status = AsyncMock(return_value=toggled_account)
        mocks["bank_repo"].get_by_id = AsyncMock(return_value=None)

        command = StateAccountCommand(account_uuid="acc-uuid-1", user_id=1)
        result = await handler.handle(command)

        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_raises_account_not_found(self, handler, mocks):
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        command = StateAccountCommand(account_uuid="nonexistent-uuid", user_id=1)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(command)

        mocks["account_repo"].switch_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_bank_name_none_when_no_bank(self, handler, mocks):
        account = self._make_account()
        account.bank_id = None
        toggled = self._make_account(is_active=False)
        toggled.bank_id = None
        toggled.bank_name = None
        toggled.bank_code = None

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["account_repo"].switch_status = AsyncMock(return_value=toggled)

        command = StateAccountCommand(account_uuid="acc-uuid-1", user_id=1)
        result = await handler.handle(command)

        assert result.bank_name is None
        assert result.bank_code is None
