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
from domain.repositories.bank_repository import BankRepository
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import AccountNotFoundError, InvalidAccountSettingsError
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
        investment_settings_repository: InvestmentCardSettingsRepository,
        bank_repository: BankRepository,
        uow: AbstractUnitOfWork,
    ):
        self.account_repository = account_repository
        self.credit_card_settings_repository = credit_card_settings_repository
        self.investment_settings_repository = investment_settings_repository
        self.bank_repository = bank_repository
        self.uow = uow

    async def handle(self, command: UpdateAccountSettingsCommand) -> AccountResponseDTO:
        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=command.account_uuid, user_id=command.user_id
        )

        if not account:
            raise AccountNotFoundError(command.account_uuid)

        async with self.uow:
            if command.credit_card_settings:
                if account.account_type != AccountType.CREDIT_CARD:
                    raise InvalidAccountSettingsError(command.account_uuid)

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
                if account.account_type != AccountType.INVESTMENT:
                    raise InvalidAccountSettingsError(command.account_uuid)

                inv_settings = InvestmentCardSettings(
                    investment_type=command.investment_settings.investment_type,
                    investment_rate=command.investment_settings.investment_rate,
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

            await self.uow.commit()

        bank_name = None
        bank_code = None
        if account.bank_id:
            bank = await self.bank_repository.get_by_id(account.bank_id)
            if bank:
                bank_name = bank.name
                bank_code = bank.code

        return AccountResponseDTO(
            account_uuid=account.uuid,
            name=account.name,
            account_type=account.account_type,
            bank_id=account.bank_id,
            bank_name=bank_name,
            bank_code=bank_code,
            current_balance=account.current_balance.amount,
            currency=account.current_balance.currency,
            is_active=account.is_active,
            credit_card_settings=command.credit_card_settings,
            investment_settings=command.investment_settings,
        )
