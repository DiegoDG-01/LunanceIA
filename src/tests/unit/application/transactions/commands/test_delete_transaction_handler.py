import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime, timezone

from application.transactions.commands.delete_transaction import (
    DeleteTransactionCommand,
    DeleteTransactionHandler,
)
from domain.entities.account import Account
from domain.entities.transaction import Transaction
from domain.objects.enums import AccountType, TransactionType
from domain.objects.money import Money
from shared.exceptions.domain import TransactionNotFoundError, AccountNotFoundError


@pytest.mark.unit
class TestDeleteTransactionHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        return {
            "transaction_repo": MagicMock(),
            "account_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return DeleteTransactionHandler(
            transaction_repository=mocks["transaction_repo"],
            account_repository=mocks["account_repo"],
            uow=mocks["uow"],
        )

    def _make_account(self, balance: str = "800.00") -> Account:
        return Account(
            id=10,
            uuid="acc-uuid-1",
            user_id=1,
            bank_id=1,
            name="Test Account",
            account_type=AccountType.CHECKING,
            current_balance=Money(Decimal(balance)),
            is_active=True,
            creation_date=datetime.now(timezone.utc),
        )

    def _make_transaction(
        self,
        tx_type: TransactionType = TransactionType.EXPENSE,
        amount: str = "200.00",
    ) -> Transaction:
        return Transaction(
            id=1,
            uuid="tx-uuid-1",
            user_id=1,
            account_id=10,
            category_id=1,
            transaction_type=tx_type,
            amount=Money(Decimal(amount)),
            transaction_date=date.today(),
            description="Test",
            creation_date=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_delete_expense_restores_balance(self, handler, mocks):
        tx = self._make_transaction(TransactionType.EXPENSE, "200.00")
        account = self._make_account("800.00")

        mocks["transaction_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=tx)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].delete_by_uuid = AsyncMock(return_value=True)

        command = DeleteTransactionCommand(uuid="tx-uuid-1", user_id=1)
        result = await handler.handle(command)

        assert result is True
        assert account.current_balance.amount == Decimal("1000.00")
        mocks["account_repo"].update.assert_called_once_with(account)

    @pytest.mark.asyncio
    async def test_delete_income_restores_balance(self, handler, mocks):
        tx = self._make_transaction(TransactionType.INCOME, "500.00")
        account = self._make_account("1500.00")

        mocks["transaction_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=tx)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].delete_by_uuid = AsyncMock(return_value=True)

        command = DeleteTransactionCommand(uuid="tx-uuid-1", user_id=1)
        await handler.handle(command)

        assert account.current_balance.amount == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_raises_transaction_not_found(self, handler, mocks):
        mocks["transaction_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        command = DeleteTransactionCommand(uuid="fake-uuid", user_id=1)

        with pytest.raises(TransactionNotFoundError):
            await handler.handle(command)

        mocks["account_repo"].get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_account_not_found(self, handler, mocks):
        tx = self._make_transaction()
        mocks["transaction_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=tx)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=None)

        command = DeleteTransactionCommand(uuid="tx-uuid-1", user_id=1)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(command)
