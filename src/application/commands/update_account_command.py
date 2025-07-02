from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from application.dto.account_dto import UpdateAccountDTO, AccountResponseDTO


@dataclass
class UpdateAccountCommand:
    """Comando para actualizar cuenta."""
    dto: UpdateAccountDTO


class UpdateAccountHandler:
    """Handler para actualizar cuenta."""

    def __init__(self, account_repository: AccountRepository):
        self.account_repository = account_repository

    async def handle(self, command: UpdateAccountCommand) -> AccountResponseDTO:
        """Ejecuta el comando de actualizar cuenta."""
        dto = command.dto

        # Obtener cuenta existente
        account = await self.account_repository.get_by_id_and_user(
            dto.account_id,
            dto.user_id
        )
        if not account:
            raise ValueError("Cuenta no encontrada")

        # Actualizar campos si se proporcionan
        if dto.name is not None:
            account.name = dto.name

        if dto.bank is not None:
            account.bank = dto.bank

        # Guardar cambios
        updated_account = await self.account_repository.update(account)

        # Retornar DTO de respuesta
        return AccountResponseDTO(
            account_id=updated_account.account_id,
            user_id=updated_account.user_id,
            name=updated_account.name,
            type=updated_account.type,
            bank=updated_account.bank,
            current_balance=updated_account.current_balance.amount,
            currency=updated_account.current_balance.currency,
            is_active=updated_account.is_active,
            creation_date=updated_account.creation_date
        )
