import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime
from decimal import Decimal

from application.investments.commands.generate_daily_yields import (
    GenerateDailyYieldCommand,
    GenerateDailyYieldHandler,
)
from domain.entities.account import Account
from domain.entities.investment_yield import InvestmentYield
from domain.objects.enums import AccountType, InterestType
from domain.objects.investment_settings import InvestmentCardSettings
from domain.objects.money import Money


@pytest.mark.unit
class TestGenerateDailyYieldHandler:
    @pytest.fixture
    def mocks(self):
        uow = MagicMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        return {
            "account_repo": MagicMock(),
            "investment_yield_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return GenerateDailyYieldHandler(
            mocks["account_repo"],
            mocks["investment_yield_repo"],
            mocks["uow"],
        )

    def _make_account(
        self, id: int = 10, balance: str = "10000.00"
    ) -> Account:
        return Account(
            id=id,
            uuid=f"acc-{id}",
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
        investment_type: str = "fixed_term",
        maturity_date: date = None,
        base_principal: str = None,
    ) -> InvestmentCardSettings:
        return InvestmentCardSettings(
            investment_type=investment_type,
            investment_rate=Decimal(rate),
            interest_type=interest_type,
            maturity_date=maturity_date,
            base_principal=Decimal(base_principal) if base_principal else None,
        )

    @pytest.mark.asyncio
    async def test_processes_compound_interest_account(self, handler, mocks):
        account = self._make_account(balance="10000.00")
        account.investment_settings = self._make_settings("10.00", InterestType.COMPOUND)
        target_date = date(2026, 2, 27)

        mocks["account_repo"].get_active_investment_accounts = AsyncMock(
            return_value=[account]
        )
        mocks["investment_yield_repo"].get_by_account_and_date = AsyncMock(
            return_value=None
        )
        mocks["investment_yield_repo"].create = AsyncMock()
        mocks["account_repo"].update = AsyncMock()

        command = GenerateDailyYieldCommand(target_date=target_date)
        result = await handler.handle(command)

        assert result["processed"] == 1
        assert result["skipped"] == 0
        assert result["errors"] == 0
        mocks["investment_yield_repo"].create.assert_called_once()
        mocks["account_repo"].update.assert_called_once()

        created_yield = mocks["investment_yield_repo"].create.call_args[0][0]
        assert created_yield.yield_amount > Decimal("0")
        assert created_yield.annual_rate == Decimal("10.00")
        assert created_yield.interest_type == InterestType.COMPOUND

    @pytest.mark.asyncio
    async def test_processes_simple_interest_with_base_principal(self, handler, mocks):
        account = self._make_account(balance="10500.00")
        account.investment_settings = self._make_settings(
            "10.00", InterestType.SIMPLE, base_principal="10000.00"
        )
        target_date = date(2026, 2, 27)

        mocks["account_repo"].get_active_investment_accounts = AsyncMock(
            return_value=[account]
        )
        mocks["investment_yield_repo"].get_by_account_and_date = AsyncMock(
            return_value=None
        )
        mocks["investment_yield_repo"].create = AsyncMock()
        mocks["account_repo"].update = AsyncMock()

        command = GenerateDailyYieldCommand(target_date=target_date)
        result = await handler.handle(command)

        assert result["processed"] == 1
        created_yield = mocks["investment_yield_repo"].create.call_args[0][0]
        # Simple interest uses base_principal (10000), not current balance (10500)
        assert created_yield.principal_amount == Decimal("10000.00")
        assert created_yield.interest_type == InterestType.SIMPLE

    @pytest.mark.asyncio
    async def test_errors_account_without_settings(self, handler, mocks):
        account = self._make_account()
        account.investment_settings = None

        mocks["account_repo"].get_active_investment_accounts = AsyncMock(
            return_value=[account]
        )

        command = GenerateDailyYieldCommand(target_date=date(2026, 2, 27))
        result = await handler.handle(command)

        assert result["processed"] == 0
        assert result["errors"] == 1
        mocks["investment_yield_repo"].create.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_excluded_investment_types(self, handler, mocks):
        account = self._make_account()
        account.investment_settings = self._make_settings(investment_type="stocks")

        mocks["account_repo"].get_active_investment_accounts = AsyncMock(
            return_value=[account]
        )

        command = GenerateDailyYieldCommand(target_date=date(2026, 2, 27))
        result = await handler.handle(command)

        assert result["processed"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_past_maturity_date(self, handler, mocks):
        account = self._make_account()
        account.investment_settings = self._make_settings(maturity_date=date(2026, 1, 1))

        mocks["account_repo"].get_active_investment_accounts = AsyncMock(
            return_value=[account]
        )

        command = GenerateDailyYieldCommand(target_date=date(2026, 2, 27))
        result = await handler.handle(command)

        assert result["processed"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_idempotency_skips_existing_yield(self, handler, mocks):
        account = self._make_account()
        account.investment_settings = self._make_settings()
        existing_yield = InvestmentYield(
            id=1,
            uuid="y-1",
            account_id=10,
            yield_date=date(2026, 2, 27),
            principal_amount=Decimal("10000.00"),
            yield_amount=Decimal("2.74"),
            cumulative_balance=Decimal("10002.74"),
            annual_rate=Decimal("10.00"),
            interest_type=InterestType.COMPOUND,
        )

        mocks["account_repo"].get_active_investment_accounts = AsyncMock(
            return_value=[account]
        )
        mocks["investment_yield_repo"].get_by_account_and_date = AsyncMock(
            return_value=existing_yield
        )

        command = GenerateDailyYieldCommand(target_date=date(2026, 2, 27))
        result = await handler.handle(command)

        assert result["processed"] == 0
        assert result["skipped"] == 1
        mocks["investment_yield_repo"].create.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_active_accounts_returns_zeros(self, handler, mocks):
        mocks["account_repo"].get_active_investment_accounts = AsyncMock(
            return_value=[]
        )

        command = GenerateDailyYieldCommand(target_date=date(2026, 2, 27))
        result = await handler.handle(command)

        assert result == {"processed": 0, "skipped": 0, "errors": 0}

    @pytest.mark.asyncio
    async def test_error_in_one_account_continues_processing(self, handler, mocks):
        account_ok = self._make_account(id=10, balance="10000.00")
        account_ok.investment_settings = self._make_settings()
        account_bad = self._make_account(id=20, balance="5000.00")
        account_bad.investment_settings = self._make_settings()

        mocks["account_repo"].get_active_investment_accounts = AsyncMock(
            return_value=[account_bad, account_ok]
        )
        # account_bad (id=20) triggers a DB error, account_ok (id=10) returns None
        mocks["investment_yield_repo"].get_by_account_and_date = AsyncMock(
            side_effect=[Exception("DB error"), None]
        )
        mocks["investment_yield_repo"].create = AsyncMock()
        mocks["account_repo"].update = AsyncMock()

        command = GenerateDailyYieldCommand(target_date=date(2026, 2, 27))
        result = await handler.handle(command)

        assert result["processed"] == 1
        assert result["errors"] == 1

    @pytest.mark.asyncio
    async def test_balance_updated_after_yield(self, handler, mocks):
        account = self._make_account(balance="10000.00")
        account.investment_settings = self._make_settings("10.00", InterestType.COMPOUND)

        mocks["account_repo"].get_active_investment_accounts = AsyncMock(
            return_value=[account]
        )
        mocks["investment_yield_repo"].get_by_account_and_date = AsyncMock(
            return_value=None
        )
        mocks["investment_yield_repo"].create = AsyncMock()
        mocks["account_repo"].update = AsyncMock()

        command = GenerateDailyYieldCommand(target_date=date(2026, 2, 27))
        await handler.handle(command)

        # Account balance should have been updated to include the yield
        assert account.current_balance.amount > Decimal("10000.00")
        mocks["account_repo"].update.assert_called_once_with(account)
