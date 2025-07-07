from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.services.account_service import AccountService


@dataclass
class DeleteAccountCommand:
    """Comando para eliminar cuenta."""

    account_id: int
    user_uuid: str


class DeleteAccountHandler:
    """Handler para eliminar cuenta."""

    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        account_service: AccountService,
    ):
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.account_service = account_service

    async def handle(self, command: DeleteAccountCommand) -> bool:
        """Ejecuta el comando de eliminar cuenta."""
        # Obtener cuenta
        account = await self.account_repository.get_by_id_and_user_uuid(
            command.account_id, command.user_uuid
        )
        if not account:
            raise ValueError("Cuenta no encontrada")

        # Validar que se puede eliminar
        if not self.account_service.validate_account_for_deletion(account):
            raise ValueError("No se puede eliminar cuenta con balance diferente a cero")

        # Verificar que no hay transacciones pendientes
        transactions = await self.transaction_repository.get_by_account(
            command.account_id, command.user_uuid
        )
        if transactions:
            raise ValueError("No se puede eliminar cuenta con transacciones existentes")

        # Eliminar cuenta
        return await self.account_repository.delete(account)
