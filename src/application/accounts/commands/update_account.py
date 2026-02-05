from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.objects.money import Money
from application.dto.account_dto import UpdateAccountDTO, AccountResponseDTO
from domain.repositories.bank_repository import BankRepository


@dataclass
class UpdateAccountCommand:
    """Comando para actualizar cuenta."""

    dto: UpdateAccountDTO


class UpdateAccountHandler:
    """Handler para actualizar cuenta."""

    def __init__(
        self, account_repository: AccountRepository, bank_repository: BankRepository
    ):
        self.account_repository = account_repository
        self.bank_repository = bank_repository

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
        updated_account = await self.account_repository.update(account)

        bank = await self.bank_repository.get_by_id(account.bank_id)
        if not bank:
            raise ValueError("Banco no encontrado")

        updated_account.bank_name = bank.name
        updated_account.bank_code = bank.code

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
        )
