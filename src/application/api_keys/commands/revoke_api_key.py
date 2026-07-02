from dataclasses import dataclass

from domain.repositories.api_key_repository import APIKeyRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork


@dataclass
class RevokeAPIKeyCommand:
    uuid: str
    user_id: int


class RevokeAPIKeyHandler:
    def __init__(
        self,
        api_key_repository: APIKeyRepository,
        uow: AbstractUnitOfWork,
    ):
        self.api_key_repository = api_key_repository
        self.uow = uow

    async def handle(self, command: RevokeAPIKeyCommand) -> bool:
        async with self.uow:
            revoked = await self.api_key_repository.revoke(
                command.uuid, command.user_id
            )
            if revoked:
                await self.uow.commit()
        return revoked
