import pytest
from unittest.mock import MagicMock, AsyncMock

from application.accounts.commands.delete_account import (
    DeleteAccountCommand,
    DeleteAccountHandler,
)
from domain.entities.account import Account
from domain.objects.enums import AccountType
from domain.objects.money import Money
from domain.services.account_service import AccountService
from shared.exceptions.domain import AccountNotFoundError
from decimal import Decimal
from datetime import datetime


@pytest.mark.unit
class TestDeleteAccountHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        account_service = MagicMock(spec=AccountService)
        account_service.validate_account_for_deletion = MagicMock(return_value=True)
        return {
            "account_repo": MagicMock(),
            "transaction_repo": MagicMock(),
            "account_service": account_service,
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return DeleteAccountHandler(
            account_repository=mocks["account_repo"],
            transaction_repository=mocks["transaction_repo"],
            account_service=mocks["account_service"],
            uow=mocks["uow"],
        )

    def _make_account(self, balance: str = "0.00") -> Account:
        return Account(
            id=10,
            uuid="acc-uuid-1",
            user_id=1,
            bank_id=1,
            name="Test Account",
            account_type=AccountType.SAVINGS,
            current_balance=Money(Decimal(balance)),
            is_active=True,
            creation_date=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_delete_success(self, handler, mocks):
        account = self._make_account()
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["transaction_repo"].get_by_account = AsyncMock(return_value=[])
        mocks["account_repo"].delete = AsyncMock(return_value=True)

        command = DeleteAccountCommand(account_uuid="acc-uuid-1", user_id=1)
        result = await handler.handle(command)

        assert result is True
        mocks["account_repo"].delete.assert_called_once_with(account)

    @pytest.mark.asyncio
    async def test_raises_account_not_found(self, handler, mocks):
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        command = DeleteAccountCommand(account_uuid="nonexistent-uuid", user_id=1)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(command)

        mocks["account_repo"].delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_has_transactions(self, handler, mocks):
        account = self._make_account()
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["transaction_repo"].get_by_account = AsyncMock(return_value=[MagicMock()])

        command = DeleteAccountCommand(account_uuid="acc-uuid-1", user_id=1)

        with pytest.raises(ValueError, match="transacciones"):
            await handler.handle(command)

        mocks["account_repo"].delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_service_validation_fails(self, handler, mocks):
        account = self._make_account(balance="500.00")
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["account_service"].validate_account_for_deletion = MagicMock(
            return_value=False
        )

        command = DeleteAccountCommand(account_uuid="acc-uuid-1", user_id=1)

        with pytest.raises(ValueError):
            await handler.handle(command)
