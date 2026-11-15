from dataclasses import dataclass
from typing import cast

from application.dto.transaction_dto import TransactionResponseDTO
from application.transactions.queries.get_transactions import link_security_trades
from domain.repositories.securities.trade_repository import SecurityTradeRepository
from domain.repositories.transactions.transaction_repository import (
    TransactionRepository,
)
from shared.exceptions.domain import TransactionNotFoundError


@dataclass
class GetTransactionByUuidQuery:
    uuid: str
    user_id: int


class GetTransactionByUuidHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        security_trade_repository: SecurityTradeRepository | None = None,
    ):
        self.transaction_repository = transaction_repository
        self.security_trade_repository = security_trade_repository

    async def handle(self, query: GetTransactionByUuidQuery) -> TransactionResponseDTO:
        transaction = (
            await self.transaction_repository.get_by_uuid_with_account_details(
                query.uuid, query.user_id
            )
        )

        if not transaction:
            raise TransactionNotFoundError(query.uuid)

        dto = TransactionResponseDTO.from_entity(
            transaction[0],
            transaction[1],
            transaction[2],
            cast(str, transaction[3]),
            transaction[4],
        )
        await link_security_trades(
            self.security_trade_repository, [(cast(int, transaction[0].id), dto)]
        )
        return dto
