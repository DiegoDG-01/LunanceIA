from dataclasses import dataclass
from typing import cast

from application.dto.investment_position_dto import PositionResponseDTO
from application.investments.services.position_overflow import PositionOverflowService
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from shared.exceptions.domain import InvestmentPositionNotFoundError


@dataclass
class GetPositionQuery:
    position_uuid: str
    user_id: int


class GetPositionHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        position_repository: InvestmentPositionRepository,
        overflow_service: PositionOverflowService,
    ):
        self.account_repository = account_repository
        self.position_repository = position_repository
        self.overflow_service = overflow_service

    async def handle(self, query: GetPositionQuery) -> PositionResponseDTO:
        position = await self.position_repository.get_by_uuid_and_user_id(
            position_uuid=query.position_uuid, user_id=query.user_id
        )
        if not position:
            raise InvestmentPositionNotFoundError(query.position_uuid)

        account = await self.account_repository.get_by_id(
            account_id=position.account_id
        )

        return PositionResponseDTO.from_entity(
            position,
            account_uuid=cast(str, account.uuid) if account else "",
            account_available_balance=account.current_balance.amount
            if account
            else None,
            overflow_position_uuid=await self.overflow_service.target_uuid(position),
        )
