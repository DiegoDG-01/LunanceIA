from dataclasses import dataclass
from typing import Optional

from application.dto.account_dto import (
    CreditCardSettingsDTO,
    InvestmentCardSettingsDTO,
    AccountResponseDTO,
)
from domain.objects.enums import AccountType
from domain.repositories.account_repository import AccountRepository
from domain.repositories.credit_card_repository import CreditCardSettingsRepository
from shared.exceptions.domain import AccountNotFoundError
from domain.objects.credit_card_settings import CreditCardSettings
from domain.objects.investment_settings import InvestmentCardSettings


@dataclass
class UpdateAccountSettingsCommand:
    account_uuid: str
    user_id: int
    credit_card_settings: Optional[CreditCardSettingsDTO] = None
    investment_settings: Optional[InvestmentCardSettingsDTO] = None


class UpdateAccountSettingsHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        credit_card_settings_repository: CreditCardSettingsRepository,
        investment_settings_repository: CreditCardSettingsRepository,
    ):
        self.account_repository = account_repository
        self.credit_card_settings_repository = credit_card_settings_repository
        self.investment_settings_repository = investment_settings_repository

    async def handle(self, command: UpdateAccountSettingsCommand) -> AccountResponseDTO:
        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=command.account_uuid, user_id=command.user_id
        )

        if not account:
            raise AccountNotFoundError(command.account_uuid)

        if command.credit_card_settings:
            if account.account_type != AccountType.CREDIT_CARD:
                raise ValueError(
                    "Credit card settings can only be set for credit accounts"
                )

            cc_settings = CreditCardSettings(
                billing_cycle_day=command.credit_card_settings.billing_cycle_day,
                payment_due_day=command.credit_card_settings.payment_due_day,
                credit_limit=command.credit_card_settings.credit_limit,
                minimum_payment_percentage=command.credit_card_settings.minimum_payment_percentage,
            )

            existing = await self.credit_card_settings_repository.get_by_account_id(
                account.id
            )
            if existing:
                await self.credit_card_settings_repository.update(
                    account.id, cc_settings
                )
            else:
                await self.credit_card_settings_repository.create(
                    account.id, cc_settings
                )

        if command.investment_settings:
            inv_settings = InvestmentCardSettings(
                investment_type=command.investment_settings.investment_type,
                interest_rate=command.investment_settings.interest_rate,
                lock_period_end_date=command.investment_settings.lock_period_end_date,
                maturity_date=command.investment_settings.maturity_date,
                early_withdrawal_penalty=command.investment_settings.early_withdrawal_penalty,
            )

            existing = await self.investment_settings_repository.get_by_account_id(
                account.id
            )
            if existing:
                await self.investment_settings_repository.update(
                    account.id, inv_settings
                )
            else:
                await self.investment_settings_repository.create(
                    account.id, inv_settings
                )

        return AccountResponseDTO(
            account_uuid=account.uuid,
            name=account.name,
            account_type=account.account_type,
            bank=account.bank,
            current_balance=account.current_balance.amount,
            currency=account.current_balance.currency,
            is_active=account.is_active,
            credit_card_settings=command.credit_card_settings,
            investment_settings=command.investment_settings,
        )
