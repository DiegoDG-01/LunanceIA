from dataclasses import dataclass
from typing import List

from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_yield_repository import InvestmentYieldRepository
from application.dto.investment_yield_dto import InvestmentYieldResponseDTO
from shared.exceptions.domain import AccountNotFoundError


@dataclass
class GetInvestmentYieldsQuery:
    account_uuid: str
    user_id: int
    limit: int = 365
    offset: int = 0


class GetInvestmentYieldsHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        investment_yield_repository: InvestmentYieldRepository,
    ) :
        self.account_repository = account_repository
        self.investment_yield_repository = investment_yield_repository

    async def handle(self, query: GetInvestmentYieldsQuery) -> List[InvestmentYieldResponseDTO]:
        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=query.account_uuid, user_id=query.user_id
        )
        if not account:
            raise AccountNotFoundError(account_uuid=query.account_uuid)

        yields = await self.investment_yield_repository.get_by_account_id(
            account_id=account.id, limit=query.limit, offset=query.offset
        )

        return [InvestmentYieldResponseDTO.from_entity(y) for y in yields]