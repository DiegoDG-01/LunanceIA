from dataclasses import dataclass

from domain.repositories.api_key_repository import APIKeyRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork


@dataclass
class DeleteAPIKeyCommand:
    uuid: str
    user_id: int


class DeleteAPIKeyHandler:
    def __init__(
        self,
        api_key_repository: APIKeyRepository,
        uow: AbstractUnitOfWork,
    ):
        self.api_key_repository = api_key_repository
        self.uow = uow

    async def handle(self, command: DeleteAPIKeyCommand) -> bool:
        async with self.uow:
            deleted = await self.api_key_repository.delete(
                command.uuid, command.user_id
            )
            if deleted:
                await self.uow.commit()
        return deleted
