from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.objects.money import Money
from domain.objects.credit_card_settings import CreditCardSettings
from domain.objects.investment_settings import InvestmentCardSettings
from application.dto.account_dto import UpdateAccountDTO, AccountResponseDTO
from domain.repositories.bank_repository import BankRepository
from domain.repositories.credit_card_repository import CreditCardSettingsRepository
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork


@dataclass
class UpdateAccountCommand:
    """Comando para actualizar cuenta."""

    dto: UpdateAccountDTO


class UpdateAccountHandler:
    """Handler para actualizar cuenta."""

    def __init__(
        self,
        account_repository: AccountRepository,
        bank_repository: BankRepository,
        credit_card_settings_repository: CreditCardSettingsRepository,
        investment_settings_repository: InvestmentCardSettingsRepository,
        uow: AbstractUnitOfWork,
    ):
        self.account_repository = account_repository
        self.bank_repository = bank_repository
        self.credit_card_settings_repository = credit_card_settings_repository
        self.investment_settings_repository = investment_settings_repository
        self.uow = uow

    async def handle(self, command: UpdateAccountCommand) -> AccountResponseDTO:
        """Ejecuta el comando de actualizar cuenta."""
        dto = command.dto

        # Obtener cuenta existente
        account = await self.account_repository.get_by_uuid_and_user_id(
            dto.account_uuid, dto.user_id
        )
        if not account:
            raise ValueError("Cuenta no encontrada")

        # Actualizar campos si se proporcionan
        if dto.name is not None:
            account.name = dto.name

        if dto.bank_id is not None:
            account.bank_id = dto.bank_id

        if dto.current_balance is not None:
            # Convertir Decimal a Money manteniendo la moneda actual
            current_currency = account.current_balance.currency
            account.current_balance = Money(dto.current_balance, current_currency)

        # Guardar cambios
        async with self.uow:
            updated_account = await self.account_repository.update(account)

            # Update settings if provided
            cc_settings_dto = None
            inv_settings_dto = None

            if dto.credit_card_settings:
                cc_settings_dto = CreditCardSettings(
                    billing_cycle_day=dto.credit_card_settings.billing_cycle_day,
                    payment_due_day=dto.credit_card_settings.payment_due_day,
                    credit_limit=dto.credit_card_settings.credit_limit,
                    minimum_payment_percentage=dto.credit_card_settings.minimum_payment_percentage,
                )
                await self.credit_card_settings_repository.update(
                    updated_account.id, cc_settings_dto
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
                await self.investment_settings_repository.update(
                    updated_account.id, inv_settings_dto
                )
                inv_settings_dto = dto.investment_settings

            bank = await self.bank_repository.get_by_id(account.bank_id)
            await self.uow.commit()
        updated_account.bank_name = bank.name if bank else None
        updated_account.bank_code = bank.code if bank else None

        # Retornar DTO de respuesta
        return AccountResponseDTO(
            account_uuid=updated_account.uuid,
            name=updated_account.name,
            account_type=updated_account.account_type,
            bank_id=updated_account.bank_id,
            bank_name=updated_account.bank_name,
            bank_code=updated_account.bank_code,
            current_balance=updated_account.current_balance.amount,
            currency=updated_account.current_balance.currency,
            is_active=updated_account.is_active,
            credit_card_settings=cc_settings_dto,
            investment_settings=inv_settings_dto,
        )
