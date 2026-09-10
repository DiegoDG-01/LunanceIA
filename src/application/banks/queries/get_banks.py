from dataclasses import dataclass

from application.dto.bank_dto import BankResponseDTO
from domain.repositories.bank_repository import BankRepository


@dataclass
class GetBanksQuery:
    only_active: bool = True
    country: str | None = None


class GetBanksHandler:
    def __init__(self, bank_repository: BankRepository):
        self.bank_repository = bank_repository

    async def handle(self, query: GetBanksQuery) -> list[BankResponseDTO]:
        banks = await self.bank_repository.get_all()

        if query.only_active:
            banks = [bank for bank in banks if bank.is_active]

        return [BankResponseDTO.from_entity(bank) for bank in banks]
