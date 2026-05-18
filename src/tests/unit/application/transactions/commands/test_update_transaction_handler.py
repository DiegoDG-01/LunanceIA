import pytest
from unittest.mock import MagicMock, AsyncMock
from decimal import Decimal
from datetime import date, datetime, timezone

from application.transactions.commands.update_transaction import (
    UpdateTransactionCommand,
    UpdateTransactionCommandHandler,
)
from domain.entities.account import Account
from domain.entities.transaction import Transaction
from domain.objects.enums import AccountType, TransactionType
from domain.objects.money import Money
from application.dto.transaction_dto import TransactionResponseDTO
from shared.exceptions.domain import TransactionNotFoundError, AccountNotFoundError


@pytest.mark.unit
class TestUpdateTransactionCommandHandler:
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
        return UpdateTransactionCommandHandler(
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
            description="Original description",
            creation_date=datetime.now(timezone.utc),
        )

    def _make_response_dto(self) -> TransactionResponseDTO:
        return TransactionResponseDTO(
            uuid="tx-uuid-1",
            account_uuid="acc-uuid-1",
            account_name="Test Account",
            account_type=AccountType.CHECKING,
            category="Food",
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal("150.00"),
            description="Updated description",
            notes=None,
            transaction_date=date.today(),
            creation_date=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_raises_transaction_not_found(self, handler, mocks):
        mocks["transaction_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        command = UpdateTransactionCommand(
            transaction_uuid="fake-uuid", user_id=1, amount=Decimal("100.00")
        )

        with pytest.raises(TransactionNotFoundError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_raises_account_not_found(self, handler, mocks):
        tx = self._make_transaction()
        mocks["transaction_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=tx)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=None)

        command = UpdateTransactionCommand(transaction_uuid="tx-uuid-1", user_id=1)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_update_reverses_and_reapplies_expense(self, handler, mocks):
        tx = self._make_transaction(TransactionType.EXPENSE, "200.00")
        account = self._make_account("800.00")
        response_dto = self._make_response_dto()

        mocks["transaction_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=tx)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["transaction_repo"].update = AsyncMock()
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].get_by_uuid_with_account_details = AsyncMock(
            return_value=(
                tx,
                "Test Account",
                AccountType.CHECKING,
                "acc-uuid-1",
                "Food",
            )
        )

        command = UpdateTransactionCommand(
            transaction_uuid="tx-uuid-1",
            user_id=1,
            amount=Decimal("150.00"),
            description="Updated description",
        )
        await handler.handle(command)

        # After reversal: 800 + 200 = 1000; after new expense 150: 1000 - 150 = 850
        assert account.current_balance.amount == Decimal("850.00")

    @pytest.mark.asyncio
    async def test_update_description_only(self, handler, mocks):
        tx = self._make_transaction(TransactionType.INCOME, "500.00")
        account = self._make_account("1500.00")

        mocks["transaction_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=tx)
        mocks["account_repo"].get_by_id = AsyncMock(return_value=account)
        mocks["transaction_repo"].update = AsyncMock()
        mocks["account_repo"].update = AsyncMock()
        mocks["transaction_repo"].get_by_uuid_with_account_details = AsyncMock(
            return_value=(tx, "Test Account", AccountType.CHECKING, "acc-uuid-1", None)
        )

        command = UpdateTransactionCommand(
            transaction_uuid="tx-uuid-1",
            user_id=1,
            description="New description",
        )
        await handler.handle(command)

        assert tx.description == "New description"
