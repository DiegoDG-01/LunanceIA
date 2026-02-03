import pytest
from unittest.mock import MagicMock, AsyncMock
from application.accounts.commands.create_account import CreateAccountCommand, CreateAccountHandler
from application.dto.account_dto import CreateAccountDTO
from domain.entities.user import User
from domain.entities.account import Account
from domain.objects.money import Money
from decimal import Decimal

@pytest.mark.unit
class TestCreateAccountHandler:
    @pytest.fixture
    def mock_account_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_user_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_credit_card_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_investment_repo(self):
        return MagicMock()

    @pytest.fixture
    def handler(self, mock_account_repo, mock_user_repo, mock_credit_card_repo, mock_investment_repo):
        return CreateAccountHandler(mock_account_repo, mock_user_repo, mock_credit_card_repo, mock_investment_repo)

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, mock_account_repo, mock_user_repo):
        # 1. Setup Mocks
        user_id = 1
        mock_user = User(id=user_id, uuid="u-1", auth0_id="a-1", name="Test", email="t@t.com", is_active=True)
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

        # Simular que el repo guarda la cuenta y devuelve una con UUID
        saved_account = MagicMock(spec=Account)
        saved_account.uuid = "acc-uuid-123"
        saved_account.name = "Test Account"
        saved_account.account_type = "SAVINGS"
        saved_account.current_balance = Money(Decimal("100.00"))
        saved_account.bank = "Bank"
        saved_account.is_active = True

        mock_account_repo.create = AsyncMock(return_value=saved_account)

        # 2. Execute
        dto = CreateAccountDTO(
            user_id=user_id,
            name="Test Account",
            account_type="SAVINGS",
            bank="Bank",
            initial_balance=Decimal("100.00"),
            currency="MXN"
        )
        command = CreateAccountCommand(dto=dto)
        result = await handler.handle(command)

        # 3. Assertions
        assert result.account_uuid == "acc-uuid-123"
        mock_user_repo.get_by_id.assert_called_once_with(user_id)
        mock_account_repo.create.assert_called_once()
        # Verificar que se creó con los datos correctos
        args, _ = mock_account_repo.create.call_args
        created_account = args[0]
        assert created_account.name == "Test Account"
        assert created_account.user_id == user_id

    @pytest.mark.asyncio
    async def test_handle_user_not_found_fails(self, handler, mock_user_repo):
        # 1. Setup Mock to return None (user not found)
        mock_user_repo.get_by_id = AsyncMock(return_value=None)

        # 2. Execute & Assert
        dto = CreateAccountDTO(user_id=99, name="X", account_type="CASH", bank="B", initial_balance=0, currency="MXN")
        command = CreateAccountCommand(dto=dto)

        with pytest.raises(ValueError, match="User not found"):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_handle_user_inactive_fails(self, handler, mock_user_repo):
        # 1. Setup Mock with inactive user
        mock_user = User(id=1, uuid="u-1", auth0_id="a-1", name="T", email="t@t.com", is_active=False)
        mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

        # 2. Execute & Assert
        dto = CreateAccountDTO(user_id=1, name="X", account_type="CASH", bank="B", initial_balance=0, currency="MXN")
        command = CreateAccountCommand(dto=dto)

        with pytest.raises(ValueError, match="User is inactive"):
            await handler.handle(command)
