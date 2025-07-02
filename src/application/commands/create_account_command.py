from dataclasses import dataclass

from domain.entities.account import Account
from domain.repositories.account_repository import AccountRepository
from domain.repositories.user_repository import UserRepository
from domain.objects.money import Money
from application.dto.account_dto import CreateAccountDTO, AccountResponseDTO


@dataclass
class CreateAccountCommand:
    """
    Command for creating an account
    """
    dto: CreateAccountDTO

class CreateAccountHandler:
    """
    Handler for creating an account
    """
    def __init__(
            self,
            account_repository: AccountRepository,
            user_repository: UserRepository
    ):

        self.account_repository = account_repository
        self.user_repository = user_repository


    async def handle(self, command: CreateAccountCommand) -> AccountResponseDTO:
        """
        Handler for creating an account
        """
        dto = command.dto

        # Validate user exists
        user = await self.user_repository.get_by_uuid(dto.user_uuid)

        if not user:
            raise ValueError("User not found")

        if not user.is_active:
            raise ValueError("User is inactive")

        # Create entity to domain
        initial_balance = Money(amount=dto.initial_balance, currency=dto.currency)
        account = Account.create_new(
            user_uuid=dto.user_uuid,
            name=dto.name,
            account_type=dto.account_type,
            bank=dto.bank,
            initial_balance=initial_balance
        )

        saved_account = await self.account_repository.create(account)

        return AccountResponseDTO(
            account_id=saved_account.account_id,
            user_id=saved_account.user_id,
            name=saved_account.name,
            account_type=saved_account.account_type,
            current_balance=saved_account.current_balance.amount,
            currency=saved_account.current_balance.currency,
            bank=saved_account.bank,
            is_active=saved_account.is_active,
            creation_date=saved_account.creation_date
        )