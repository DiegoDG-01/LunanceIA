from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.services.account_service import AccountService

from shared.exceptions.domain import AccountNotFoundError


@dataclass
class DeleteAccountCommand:
    """Comando para eliminar cuenta."""

    account_uuid: str
    user_id: int


class DeleteAccountHandler:
    """Handler para eliminar cuenta."""

    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        account_service: AccountService,
        uow: AbstractUnitOfWork,
    ):
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.account_service = account_service
        self.uow = uow

    async def handle(self, command: DeleteAccountCommand) -> bool:
        """Ejecuta el comando de eliminar cuenta."""
        # Obtener cuenta
        account = await self.account_repository.get_by_uuid_and_user_id(
            command.account_uuid, command.user_id
        )
        if not account:
            # raise ValueError("Cuenta no encontrada")
            raise AccountNotFoundError(command.account_uuid)

        # Validar que se puede eliminar
        if not self.account_service.validate_account_for_deletion(account):
            raise ValueError("No se puede eliminar cuenta con balance diferente a cero")

        # Verificar que no hay transacciones pendientes
        transactions = await self.transaction_repository.get_by_account(
            command.account_uuid, command.user_id
        )
        if transactions:
            raise ValueError("No se puede eliminar cuenta con transacciones existentes")

        # Eliminar cuenta
        async with self.uow:
            result = await self.account_repository.delete(account)
            await self.uow.commit()

        return result
