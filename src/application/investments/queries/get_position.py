from dataclasses import dataclass
from typing import cast

from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from application.dto.investment_position_dto import PositionResponseDTO
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
    ):
        self.account_repository = account_repository
        self.position_repository = position_repository

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
        )
