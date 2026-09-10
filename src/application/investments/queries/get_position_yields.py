from dataclasses import dataclass
from typing import cast

from application.dto.investment_yield_dto import InvestmentYieldResponseDTO
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from domain.repositories.investment_yield_repository import InvestmentYieldRepository
from shared.exceptions.domain import InvestmentPositionNotFoundError


@dataclass
class GetPositionYieldsQuery:
    position_uuid: str
    user_id: int
    limit: int = 365
    offset: int = 0


class GetPositionYieldsHandler:
    def __init__(
        self,
        position_repository: InvestmentPositionRepository,
        investment_yield_repository: InvestmentYieldRepository,
    ):
        self.position_repository = position_repository
        self.investment_yield_repository = investment_yield_repository

    async def handle(
        self, query: GetPositionYieldsQuery
    ) -> list[InvestmentYieldResponseDTO]:
        position = await self.position_repository.get_by_uuid_and_user_id(
            position_uuid=query.position_uuid, user_id=query.user_id
        )
        if not position:
            raise InvestmentPositionNotFoundError(query.position_uuid)

        yields = await self.investment_yield_repository.get_by_position_id(
            position_id=cast(int, position.id), limit=query.limit, offset=query.offset
        )

        return [InvestmentYieldResponseDTO.from_entity(y) for y in yields]
