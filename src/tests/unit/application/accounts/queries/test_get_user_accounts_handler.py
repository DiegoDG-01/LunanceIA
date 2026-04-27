import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import datetime

from application.accounts.queries.get_user_accounts import (
    GetUserAccountsQuery,
    GetUserAccountsHandler,
)
from domain.entities.account import Account
from domain.objects.enums import AccountType
from domain.objects.money import Money


@pytest.mark.unit
class TestGetUserAccountsHandler:
    @pytest.fixture
    def mock_account_repo(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_account_repo):
        return GetUserAccountsHandler(account_repository=mock_account_repo)

    def _make_account(self, account_id: int = 1, is_active: bool = True) -> Account:
        account = Account(
            id=account_id,
            uuid=f"acc-uuid-{account_id}",
            user_id=1,
            bank_id=1,
            name=f"Account {account_id}",
            account_type=AccountType.SAVINGS,
            current_balance=Money(Decimal("500.00")),
            is_active=is_active,
            creation_date=datetime.now(),
        )
        account.bank_name = "BBVA"
        account.bank_code = "BBV"
        account.credit_card_settings = None
        account.investment_settings = None
        return account

    @pytest.mark.asyncio
    async def test_returns_all_accounts(self, handler, mock_account_repo):
        accounts = [self._make_account(1), self._make_account(2)]
        mock_account_repo.get_by_user_id = AsyncMock(return_value=accounts)

        query = GetUserAccountsQuery(user_id=1, only_active=False)
        result = await handler.handle(query)

        assert len(result) == 2
        assert result[0].account_uuid == "acc-uuid-1"
        assert result[1].account_uuid == "acc-uuid-2"
        mock_account_repo.get_by_user_id.assert_called_once_with(
            user_id=1, limit=50, offset=0
        )

    @pytest.mark.asyncio
    async def test_returns_only_active_accounts(self, handler, mock_account_repo):
        active_accounts = [self._make_account(1, is_active=True)]
        mock_account_repo.get_active_by_user = AsyncMock(return_value=active_accounts)

        query = GetUserAccountsQuery(user_id=1, only_active=True)
        result = await handler.handle(query)

        assert len(result) == 1
        mock_account_repo.get_active_by_user.assert_called_once_with(
            user_id=1, limit=50, offset=0
        )
        mock_account_repo.get_by_user_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_accounts(self, handler, mock_account_repo):
        mock_account_repo.get_by_user_id = AsyncMock(return_value=[])

        query = GetUserAccountsQuery(user_id=1)
        result = await handler.handle(query)

        assert result == []

    @pytest.mark.asyncio
    async def test_respects_limit_and_offset(self, handler, mock_account_repo):
        mock_account_repo.get_by_user_id = AsyncMock(return_value=[])

        query = GetUserAccountsQuery(user_id=1, limit=10, offset=5)
        await handler.handle(query)

        mock_account_repo.get_by_user_id.assert_called_once_with(
            user_id=1, limit=10, offset=5
        )

    @pytest.mark.asyncio
    async def test_maps_dto_fields_correctly(self, handler, mock_account_repo):
        account = self._make_account(1)
        mock_account_repo.get_by_user_id = AsyncMock(return_value=[account])

        query = GetUserAccountsQuery(user_id=1)
        result = await handler.handle(query)

        dto = result[0]
        assert dto.account_uuid == "acc-uuid-1"
        assert dto.name == "Account 1"
        assert dto.bank_name == "BBVA"
        assert dto.bank_code == "BBV"
        assert dto.current_balance == Decimal("500.00")
        assert dto.is_active is True
