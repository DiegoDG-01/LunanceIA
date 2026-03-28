import pytest
from unittest.mock import MagicMock, AsyncMock
from application.transactions.commands.create_transaction import CreateTransactionCommand, CreateTransactionHandler
from application.dto.transaction_dto import CreateTransactionDTO
from domain.entities.user import User
from domain.entities.account import Account
from domain.entities.transaction import Transaction
from domain.entities.category import Category
from domain.objects.money import Money
from domain.objects.enums import TransactionType, AccountType
from shared.exceptions.domain import UserNotFoundError, AccountNotFoundError, InsufficientFundsError
from decimal import Decimal
from datetime import date, datetime

@pytest.mark.unit
class TestCreateTransactionHandler:
    @pytest.fixture
    def mocks(self):
        uow = AsyncMock()
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=False)
        bank_repo = MagicMock()
        bank_repo.get_by_id = AsyncMock(return_value=None)
        return {
            "user_repo": MagicMock(),
            "account_repo": MagicMock(),
            "transaction_repo": MagicMock(),
            "category_repo": MagicMock(),
            "bank_repo": bank_repo,
            "investment_settings_repo": MagicMock(),
            "uow": uow,
        }

    @pytest.fixture
    def handler(self, mocks):
        return CreateTransactionHandler(
            mocks["user_repo"],
            mocks["account_repo"],
            mocks["transaction_repo"],
            mocks["category_repo"],
            mocks["bank_repo"],
            mocks["investment_settings_repo"],
            mocks["uow"],
        )

    @pytest.mark.asyncio
    async def test_create_expense_success(self, handler, mocks):
        # 1. Setup
        user_id = 1
        account_uuid = "acc-123"
        mock_user = User(id=user_id, uuid="u-1", auth0_id="a-1", name="Test", email="t@t.com", is_active=True)
        mock_account = Account(
            id=10,
            uuid=account_uuid,
            user_id=user_id,
            name="Bank",
            account_type=AccountType.CHECKING,
            current_balance=Money(Decimal("1000.00")),
            bank_id=1,
            is_active=True,
            creation_date=datetime.now()
        )
        mock_category = Category(id=1, name="Food", type="EXPENSE")

        mocks["user_repo"].get_by_id = AsyncMock(return_value=mock_user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=mock_account)
        mocks["category_repo"].get_by_id = AsyncMock(return_value=mock_category)
        mocks["account_repo"].update = AsyncMock()

        # Mocking the saved transaction return
        saved_tx = Transaction(
            id=1,
            uuid="tx-123",
            user_id=user_id,
            account_id=10,
            category_id=1,
            transaction_type=TransactionType.EXPENSE,
            amount=Money(Decimal("200.00")),
            transaction_date=date.today(),
            description="Lunch",
            notes="",
            creation_date=datetime.now()
        )

        mocks["transaction_repo"].create = AsyncMock(return_value=saved_tx)

        # 2. Execute
        dto = CreateTransactionDTO(
            user_id=user_id,
            account_uuid=account_uuid,
            category_id=1,
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal("200.00"),
            currency="MXN",
            description="Lunch"
        )
        command = CreateTransactionCommand(dto=dto)
        result = await handler.handle(command)

        # 3. Assertions
        assert result.amount == 200.00
        # Verify account balance was updated: 1000 - 200 = 800
        assert mock_account.current_balance.amount == Decimal("800.00")
        mocks["account_repo"].update.assert_called_once_with(mock_account)
        mocks["transaction_repo"].create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_income_success(self, handler, mocks):
        # 1. Setup
        user_id = 1
        account_uuid = "acc-123"
        mock_user = User(id=user_id, uuid="u-1", auth0_id="a-1", name="Test", email="t@t.com", is_active=True)
        mock_account = Account(
            id=10,
            uuid=account_uuid,
            user_id=user_id,
            name="Bank",
            account_type=AccountType.CHECKING,
            current_balance=Money(Decimal("1000.00")),
            bank_id=1,
            is_active=True,
            creation_date=datetime.now()
        )

        mocks["user_repo"].get_by_id = AsyncMock(return_value=mock_user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=mock_account)
        mocks["account_repo"].update = AsyncMock()

        saved_tx = Transaction(
            id=2,
            uuid="tx-456",
            user_id=user_id,
            account_id=10,
            category_id=2,
            transaction_type=TransactionType.INCOME,
            amount=Money(Decimal("500.00")),
            transaction_date=date.today(),
            description="Salary",
            creation_date=datetime.now()
        )

        mocks["transaction_repo"].create = AsyncMock(return_value=saved_tx)
        mocks["category_repo"].get_by_id = AsyncMock(return_value=Category(id=2, name="Job", type="INCOME"))

        # 2. Execute
        dto = CreateTransactionDTO(
            user_id=user_id,
            account_uuid=account_uuid,
            category_id=2,
            transaction_type=TransactionType.INCOME,
            amount=Decimal("500.00"),
            currency="MXN",
            description="Salary"
        )
        await handler.handle(CreateTransactionCommand(dto=dto))

        # 3. Assertion: 1000 + 500 = 1500
        assert mock_account.current_balance.amount == Decimal("1500.00")

    @pytest.mark.asyncio
    async def test_insufficient_funds_fails(self, handler, mocks):
        # 1. Setup account with only 50.00
        user_id = 1
        mock_user = User(id=user_id, uuid="u-1", auth0_id="a-1", name="T", email="t@t.com", is_active=True)
        mock_account = Account(
            id=10, uuid="acc", user_id=user_id, name="B", account_type=AccountType.CASH,
            current_balance=Money(Decimal("50.00")),
            bank_id=1, is_active=True, creation_date=datetime.now()
        )

        mocks["user_repo"].get_by_id = AsyncMock(return_value=mock_user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=mock_account)

        # 2. Execute trying to spend 100.00
        dto = CreateTransactionDTO(
            user_id=user_id, account_uuid="acc", category_id=1,
            transaction_type=TransactionType.EXPENSE, amount=Decimal("100.00"), currency="MXN"
        )

        with pytest.raises(InsufficientFundsError):
            await handler.handle(CreateTransactionCommand(dto=dto))

        # Balance should remain 50.00
        assert mock_account.current_balance.amount == Decimal("50.00")
        mocks["transaction_repo"].create.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_not_found_fails(self, handler, mocks):
        mocks["user_repo"].get_by_id = AsyncMock(return_value=None)
        dto = CreateTransactionDTO(user_id=99, account_uuid="any", category_id=1, amount=Decimal("10"), transaction_type=TransactionType.EXPENSE)

        with pytest.raises(UserNotFoundError):
            await handler.handle(CreateTransactionCommand(dto=dto))

    @pytest.mark.asyncio
    async def test_account_not_found_fails(self, handler, mocks):
        mock_user = User(id=1, uuid="u-1", auth0_id="a-1", name="T", email="t@t.com", is_active=True)
        mocks["user_repo"].get_by_id = AsyncMock(return_value=mock_user)
        mocks["account_repo"].get_by_uuid_and_user_id = AsyncMock(return_value=None)

        dto = CreateTransactionDTO(user_id=1, account_uuid="fake", category_id=1, amount=Decimal("10"), transaction_type=TransactionType.EXPENSE)

        with pytest.raises(AccountNotFoundError):
            await handler.handle(CreateTransactionCommand(dto=dto))
