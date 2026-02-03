from dataclasses import dataclass

from domain.entities.account import Account
from domain.objects.credit_card_settings import CreditCardSettings
from domain.objects.enums import AccountType
from domain.objects.investment_settings import InvestmentCardSettings
from domain.repositories.account_repository import AccountRepository
from domain.repositories.credit_card_repository import CreditCardSettingsRepository
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
)
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
        user_repository: UserRepository,
        credit_card_settings_repository: CreditCardSettingsRepository,
        investment_settings_repository: InvestmentCardSettingsRepository,
    ):
        self.account_repository = account_repository
        self.user_repository = user_repository
        self.credit_card_settings_repository = credit_card_settings_repository
        self.investment_settings_repository = investment_settings_repository

    async def handle(self, command: CreateAccountCommand) -> AccountResponseDTO:
        """
        Handler for creating an account
        """
        dto = command.dto

        # Validate user exists
        user = await self.user_repository.get_by_id(dto.user_id)

        if not user:
            raise ValueError("User not found")

        if not user.is_active:
            raise ValueError("User is inactive")

        if dto.credit_card_settings and dto.account_type != AccountType.CREDIT_CARD:
            raise ValueError("Credit card settings can only be set for credit accounts")

        if dto.investment_settings and dto.account_type != AccountType.INVESTMENT:
            raise ValueError(
                "Investment settings can only be set for investment accounts"
            )

        # Create entity to domain
        initial_balance = Money(amount=dto.initial_balance, currency=dto.currency)
        account = Account.create_new(
            user_id=dto.user_id,
            name=dto.name,
            account_type=dto.account_type,
            bank=dto.bank,
            initial_balance=initial_balance,
        )

        saved_account = await self.account_repository.create(account)

        # Create settings if provided
        cc_settings_dto = None
        inv_settings_dto = None

        if dto.credit_card_settings:
            cc_settings_dto = CreditCardSettings(
                billing_cycle_day=dto.credit_card_settings.billing_cycle_day,
                payment_due_day=dto.credit_card_settings.payment_due_day,
                credit_limit=dto.credit_card_settings.credit_limit,
                minimum_payment_percentage=dto.credit_card_settings.minimum_payment_percentage,
            )
            await self.credit_card_settings_repository.create(
                saved_account.id, cc_settings_dto
            )
            cc_settings_dto = dto.credit_card_settings

        if dto.investment_settings:
            inv_settings_dto = InvestmentCardSettings(
                investment_type=dto.investment_settings.investment_type,
                interest_rate=dto.investment_settings.interest_rate,
                lock_period_end_date=dto.investment_settings.lock_period_end_date,
                maturity_date=dto.investment_settings.maturity_date,
                early_withdrawal_penalty=dto.investment_settings.early_withdrawal_penalty,
            )
            await self.investment_settings_repository.create(
                saved_account.id, inv_settings_dto
            )
            inv_settings_dto = dto.investment_settings

        return AccountResponseDTO(
            account_uuid=saved_account.uuid,
            name=saved_account.name,
            account_type=saved_account.account_type,
            current_balance=saved_account.current_balance.amount,
            currency=saved_account.current_balance.currency,
            bank=saved_account.bank,
            is_active=saved_account.is_active,
            credit_card_settings=cc_settings_dto,
            investment_settings=inv_settings_dto,
        )
