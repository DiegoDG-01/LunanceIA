from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from application.dto.investment_position_dto import (
    AccountPositionsResponseDTO,
    PositionResponseDTO,
)
from domain.objects.enums import PositionStatus
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from shared.exceptions.domain import AccountNotFoundError


@dataclass
class ListPositionsQuery:
    account_uuid: str
    user_id: int
    include_liquidated: bool = False


class ListPositionsHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        position_repository: InvestmentPositionRepository,
    ):
        self.account_repository = account_repository
        self.position_repository = position_repository

    async def handle(self, query: ListPositionsQuery) -> AccountPositionsResponseDTO:
        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=query.account_uuid, user_id=query.user_id
        )
        if not account:
            raise AccountNotFoundError(query.account_uuid)

        positions = await self.position_repository.get_by_account_id(
            account_id=cast(int, account.id)
        )
        # Los destinos siempre son de la misma cuenta, así que el uuid sale de
        # lo ya cargado en vez de una consulta por apartado. Se arma antes de
        # filtrar para no perder el nombre de un destino ya liquidado.
        uuid_by_id = {p.id: p.uuid for p in positions}

        if not query.include_liquidated:
            positions = [p for p in positions if p.status != PositionStatus.LIQUIDATED]

        invested = sum(
            (
                p.total_value.amount
                for p in positions
                if p.status != PositionStatus.LIQUIDATED
            ),
            start=Decimal(0),
        )
        available = account.current_balance.amount

        return AccountPositionsResponseDTO(
            account_uuid=cast(str, account.uuid),
            account_name=account.name,
            available_balance=available,
            invested_balance=invested,
            total_balance=available + invested,
            currency=account.current_balance.currency,
            positions=[
                PositionResponseDTO.from_entity(
                    p,
                    cast(str, account.uuid),
                    overflow_position_uuid=uuid_by_id.get(p.overflow_position_id),
                )
                for p in positions
            ],
        )
