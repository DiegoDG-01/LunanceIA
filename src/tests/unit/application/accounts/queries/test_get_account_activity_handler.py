import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import date, datetime
from decimal import Decimal

from application.accounts.queries.get_account_activity import (
    GetAccountActivityQuery,
    GetAccountActivitiesHandler,
)
from domain.entities.account import Account
from domain.entities.transaction import Transaction
from domain.objects.enums import AccountType, TransactionType
from domain.objects.money import Money
from shared.exceptions.domain import AccountNotFoundError, TransactionNotActivityError


@pytest.mark.unit
class TestGetAccountActivitiesHandler:
    @pytest.fixture
    def mocks(self):
        return {
            "account_repo": MagicMock(),
            "transaction_repo": MagicMock(),
        }

    @pytest.fixture
    def handler(self, mocks):
        return GetAccountActivitiesHandler(
            account_repository=mocks["account_repo"],
            transaction_repository=mocks["transaction_repo"],
        )

    def _make_account(self, account_id: int = 10, uuid: str = "acc-uuid-1") -> Account:
        return Account(
            id=account_id,
            uuid=uuid,
            user_id=1,
            bank_id=None,
            name="BBVA Débito",
            account_type=AccountType.SAVINGS,
            current_balance=Money(Decimal("5000.00")),
            is_active=True,
            creation_date=datetime.now(),
        )

    def _make_transaction(
        self,
        tx_id: int = 1,
        account_id: int = 10,
        amount: str = "500.00",
        tx_type: TransactionType = TransactionType.EXPENSE,
        description: str = "Supermercado",
        tx_date: date = None,
    ) -> Transaction:
        return Transaction(
            id=tx_id,
            uuid=f"tx-uuid-{tx_id}",
            user_id=1,
            account_id=account_id,
            category_id=1,
            transaction_type=tx_type,
            amount=Money(Decimal(amount)),
            transaction_date=tx_date or date(2026, 3, 1),
            description=description,
        )

    @pytest.mark.asyncio
    async def test_returns_list_of_activity_dtos(self, handler, mocks):
        account = self._make_account()
        tx1 = self._make_transaction(1, description="Supermercado", amount="350.00")
        tx2 = self._make_transaction(
            2,
            description="Nómina",
            amount="15000.00",
            tx_type=TransactionType.INCOME,
            tx_date=date(2026, 3, 5),
        )

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["transaction_repo"].get_activity_by_account_id = AsyncMock(
            return_value=[(tx1, "Alimentos"), (tx2, "Salario")]
        )

        query = GetAccountActivityQuery(user_id=1, account_uuid="acc-uuid-1")
        result = await handler.handle(query)

        assert len(result) == 2
        assert result[0].name == "Supermercado"
        assert result[0].amount == Decimal("350.00")
        assert result[0].category_name == "Alimentos"
        assert result[0].transaction_date == date(2026, 3, 1)

        assert result[1].name == "Nómina"
        assert result[1].amount == Decimal("15000.00")
        assert result[1].category_name == "Salario"
        assert result[1].transaction_date == date(2026, 3, 5)

    @pytest.mark.asyncio
    async def test_raises_when_account_not_found(self, handler, mocks):
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        query = GetAccountActivityQuery(user_id=1, account_uuid="nonexistent-uuid")

        with pytest.raises(AccountNotFoundError):
            await handler.handle(query)

        mocks["transaction_repo"].get_activity_by_account_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_when_no_transactions_found(self, handler, mocks):
        account = self._make_account()

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["transaction_repo"].get_activity_by_account_id = AsyncMock(return_value=[])

        query = GetAccountActivityQuery(user_id=1, account_uuid="acc-uuid-1")

        with pytest.raises(TransactionNotActivityError):
            await handler.handle(query)

    @pytest.mark.asyncio
    async def test_uses_correct_account_id_for_transaction_query(self, handler, mocks):
        account = self._make_account(account_id=99)
        tx = self._make_transaction(account_id=99)

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["transaction_repo"].get_activity_by_account_id = AsyncMock(
            return_value=[(tx, "Transporte")]
        )

        query = GetAccountActivityQuery(user_id=1, account_uuid="acc-uuid-1")
        await handler.handle(query)

        mocks["transaction_repo"].get_activity_by_account_id.assert_called_once_with(
            account_id=99
        )

    @pytest.mark.asyncio
    async def test_queries_account_with_correct_uuid_and_user_id(self, handler, mocks):
        account = self._make_account(uuid="acc-uuid-42")
        tx = self._make_transaction()

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["transaction_repo"].get_activity_by_account_id = AsyncMock(
            return_value=[(tx, "Alimentos")]
        )

        query = GetAccountActivityQuery(user_id=7, account_uuid="acc-uuid-42")
        await handler.handle(query)

        mocks["account_repo"].get_by_uuid_and_user_id.assert_called_once_with(
            account_uuid="acc-uuid-42", user_id=7
        )

    @pytest.mark.asyncio
    async def test_handles_transaction_with_no_category(self, handler, mocks):
        account = self._make_account()
        tx = self._make_transaction(description="Retiro ATM")

        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=account)
        mocks["transaction_repo"].get_activity_by_account_id = AsyncMock(
            return_value=[(tx, None)]
        )

        query = GetAccountActivityQuery(user_id=1, account_uuid="acc-uuid-1")
        result = await handler.handle(query)

        assert len(result) == 1
        assert result[0].category_name is None
        assert result[0].name == "Retiro ATM"
