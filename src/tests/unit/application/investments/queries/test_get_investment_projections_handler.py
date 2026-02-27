import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import date, datetime
from decimal import Decimal

from application.investments.queries.get_investment_projections import (
    GetInvestmentProjectionsQuery,
    GetInvestmentProjectionsHandler,
)
from domain.entities.account import Account
from domain.objects.enums import AccountType, InterestType
from domain.objects.investment_settings import InvestmentCardSettings
from domain.objects.money import Money
from shared.exceptions.domain import AccountNotFoundError


@pytest.mark.unit
class TestGetInvestmentProjectionsQuery:
    def test_default_project_days_is_none(self):
        query = GetInvestmentProjectionsQuery(account_uuid="acc-1", user_id=1)
        assert query.project_days is None

    def test_custom_project_days(self):
        query = GetInvestmentProjectionsQuery(
            account_uuid="acc-1", user_id=1, project_days=90
        )
        assert query.project_days == 90


@pytest.mark.unit
class TestGetInvestmentProjectionsHandler:
    @pytest.fixture
    def mocks(self):
        return {
            "account_repo": MagicMock(),
            "investment_settings_repo": MagicMock(),
        }

    @pytest.fixture
    def handler(self, mocks):
        return GetInvestmentProjectionsHandler(
            mocks["account_repo"],
            mocks["investment_settings_repo"],
        )

    def _make_account(self, balance: str = "10000.00") -> Account:
        return Account(
            id=10,
            uuid="acc-1",
            user_id=1,
            name="Investment",
            account_type=AccountType.INVESTMENT,
            current_balance=Money(Decimal(balance)),
            bank_id=None,
            is_active=True,
            creation_date=datetime.now(),
        )

    def _make_settings(
        self,
        rate: str = "10.00",
        interest_type: InterestType = InterestType.COMPOUND,
        maturity_date: date = None,
        base_principal: str = None,
    ) -> InvestmentCardSettings:
        return InvestmentCardSettings(
            investment_type="fixed_term",
            interest_rate=Decimal(rate),
            interest_type=interest_type,
            maturity_date=maturity_date,
            base_principal=Decimal(base_principal) if base_principal else None,
        )

    @pytest.mark.asyncio
    async def test_account_not_found_raises_error(self, handler, mocks):
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        query = GetInvestmentProjectionsQuery(account_uuid="fake", user_id=1)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(query)

    @pytest.mark.asyncio
    async def test_compound_projection_with_explicit_days(self, handler, mocks):
        mock_account = self._make_account("10000.00")
        mock_settings = self._make_settings("10.00", InterestType.COMPOUND)

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=mock_account
        )
        mocks["investment_settings_repo"].get_by_account_id = AsyncMock(
            return_value=mock_settings
        )

        query = GetInvestmentProjectionsQuery(
            account_uuid="acc-1", user_id=1, project_days=30
        )
        result = await handler.handle(query)

        assert result.account_uuid == "acc-1"
        assert result.current_balance == Decimal("10000.00")
        assert result.annual_rate == Decimal("10.00")
        assert result.interest_type == InterestType.COMPOUND
        assert len(result.daily_projections) == 30
        assert result.projected_final_balance > Decimal("10000.00")
        # Each day should grow
        for i in range(1, len(result.daily_projections)):
            assert (
                result.daily_projections[i].projected_balance
                >= result.daily_projections[i - 1].projected_balance
            )

    @pytest.mark.asyncio
    async def test_simple_interest_uses_base_principal(self, handler, mocks):
        mock_account = self._make_account("10500.00")
        mock_settings = self._make_settings(
            "10.00", InterestType.SIMPLE, base_principal="10000.00"
        )

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=mock_account
        )
        mocks["investment_settings_repo"].get_by_account_id = AsyncMock(
            return_value=mock_settings
        )

        query = GetInvestmentProjectionsQuery(
            account_uuid="acc-1", user_id=1, project_days=10
        )
        result = await handler.handle(query)

        assert result.interest_type == InterestType.SIMPLE
        assert len(result.daily_projections) == 10
        # Simple interest: all days should use same principal (10000)
        for proj in result.daily_projections:
            assert proj.principal_amount == Decimal("10000.00")

    @pytest.mark.asyncio
    async def test_maturity_date_determines_days_when_no_project_days(
        self, handler, mocks
    ):
        mock_account = self._make_account("10000.00")
        maturity = date(2026, 3, 9)
        mock_settings = self._make_settings(
            "10.00", InterestType.COMPOUND, maturity_date=maturity
        )

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=mock_account
        )
        mocks["investment_settings_repo"].get_by_account_id = AsyncMock(
            return_value=mock_settings
        )

        with patch(
            "application.investments.queries.get_investment_projections.date"
        ) as mock_date:
            mock_date.today.return_value = date(2026, 2, 27)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            query = GetInvestmentProjectionsQuery(account_uuid="acc-1", user_id=1)
            result = await handler.handle(query)

        expected_days = (maturity - date(2026, 2, 27)).days
        assert len(result.daily_projections) == expected_days
        assert result.maturity_date == maturity

    @pytest.mark.asyncio
    async def test_no_settings_defaults_to_zero_rate(self, handler, mocks):
        mock_account = self._make_account("5000.00")

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=mock_account
        )
        mocks["investment_settings_repo"].get_by_account_id = AsyncMock(
            return_value=None
        )

        query = GetInvestmentProjectionsQuery(
            account_uuid="acc-1", user_id=1, project_days=5
        )
        result = await handler.handle(query)

        assert result.annual_rate == Decimal("0")
        assert result.interest_type == InterestType.COMPOUND
        # With 0% rate, balance should stay the same
        for proj in result.daily_projections:
            assert proj.yield_amount == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_project_days_capped_at_3650(self, handler, mocks):
        mock_account = self._make_account("10000.00")
        mock_settings = self._make_settings("5.00")

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(
            return_value=mock_account
        )
        mocks["investment_settings_repo"].get_by_account_id = AsyncMock(
            return_value=mock_settings
        )

        query = GetInvestmentProjectionsQuery(
            account_uuid="acc-1", user_id=1, project_days=5000
        )
        result = await handler.handle(query)

        assert len(result.daily_projections) == 3650
