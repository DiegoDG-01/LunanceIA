import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime, timezone
from decimal import Decimal

from application.investments.queries.get_investment_yields import (
    GetInvestmentYieldsQuery,
    GetInvestmentYieldsHandler,
)
from domain.entities.account import Account
from domain.entities.investment_yield import InvestmentYield
from domain.objects.enums import AccountType, InterestType
from domain.objects.money import Money
from shared.exceptions.domain import AccountNotFoundError


@pytest.mark.unit
class TestGetInvestmentYieldsQuery:
    def test_default_values(self):
        query = GetInvestmentYieldsQuery(account_uuid="acc-1", user_id=1)
        assert query.limit == 365
        assert query.offset == 0

    def test_custom_values(self):
        query = GetInvestmentYieldsQuery(
            account_uuid="acc-1", user_id=1, limit=30, offset=10
        )
        assert query.limit == 30
        assert query.offset == 10


@pytest.mark.unit
class TestGetInvestmentYieldsHandler:
    @pytest.fixture
    def mocks(self):
        return {
            "account_repo": MagicMock(),
            "investment_yield_repo": MagicMock(),
        }

    @pytest.fixture
    def handler(self, mocks):
        return GetInvestmentYieldsHandler(
            mocks["account_repo"],
            mocks["investment_yield_repo"],
        )

    @pytest.mark.asyncio
    async def test_returns_yields_for_valid_account(self, handler, mocks):
        mock_account = Account(
            id=10,
            uuid="acc-1",
            user_id=1,
            name="Investment",
            account_type=AccountType.INVESTMENT,
            current_balance=Money(Decimal("10000.00")),
            bank_id=1,
            is_active=True,
            creation_date=datetime.now(timezone.utc),
        )
        mock_yields = [
            InvestmentYield(
                id=1,
                uuid="y-1",
                account_id=10,
                yield_date=date(2026, 2, 25),
                principal_amount=Decimal("10000.00"),
                yield_amount=Decimal("2.74"),
                cumulative_balance=Decimal("10002.74"),
                annual_rate=Decimal("10.00"),
                interest_type=InterestType.COMPOUND,
                created_at=datetime.now(timezone.utc),
            ),
            InvestmentYield(
                id=2,
                uuid="y-2",
                account_id=10,
                yield_date=date(2026, 2, 26),
                principal_amount=Decimal("10002.74"),
                yield_amount=Decimal("2.74"),
                cumulative_balance=Decimal("10005.48"),
                annual_rate=Decimal("10.00"),
                interest_type=InterestType.COMPOUND,
                created_at=datetime.now(timezone.utc),
            ),
        ]

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=mock_account
        )
        mocks["investment_yield_repo"].get_by_account_id = AsyncMock(
            return_value=mock_yields
        )

        query = GetInvestmentYieldsQuery(account_uuid="acc-1", user_id=1, limit=30)
        result = await handler.handle(query)

        assert len(result) == 2
        assert result[0].uuid == "y-1"
        assert result[0].yield_amount == Decimal("2.74")
        assert result[1].uuid == "y-2"
        mocks["investment_yield_repo"].get_by_account_id.assert_called_once_with(
            account_id=10, limit=30, offset=0
        )

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_yields(self, handler, mocks):
        mock_account = Account(
            id=10,
            uuid="acc-1",
            user_id=1,
            name="Investment",
            account_type=AccountType.INVESTMENT,
            current_balance=Money(Decimal("5000.00")),
            bank_id=1,
            is_active=True,
            creation_date=datetime.now(timezone.utc),
        )

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=mock_account
        )
        mocks["investment_yield_repo"].get_by_account_id = AsyncMock(return_value=[])

        query = GetInvestmentYieldsQuery(account_uuid="acc-1", user_id=1)
        result = await handler.handle(query)

        assert result == []

    @pytest.mark.asyncio
    async def test_account_not_found_raises_error(self, handler, mocks):
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        query = GetInvestmentYieldsQuery(account_uuid="nonexistent", user_id=1)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(query)
