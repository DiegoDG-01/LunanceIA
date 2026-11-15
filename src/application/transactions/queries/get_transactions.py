from dataclasses import dataclass
from datetime import date
from typing import cast

from application.dto.transaction_dto import TransactionResponseDTO
from domain.objects.enums import TransactionType
from domain.repositories.securities.trade_repository import SecurityTradeRepository
from domain.repositories.transactions.transaction_repository import (
    TransactionRepository,
)
from shared.exceptions.domain import TransactionNotFoundError


@dataclass
class GetTransactionsQuery:
    """
    Query to get transactions
    """

    user_id: int
    account_uuid: str | None

    skip: int = 0
    limit: int = 100
    start_date: date | None = None
    end_date: date | None = None
    transaction_type: TransactionType | None = None
    category_id: int | None = None


class GetTransactionsHandler:
    """
    Handler to get transactions
    """

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        security_trade_repository: SecurityTradeRepository | None = None,
    ):
        self.transaction_repository = transaction_repository
        # Marca los movimientos que creó una operación de acciones.
        self.security_trade_repository = security_trade_repository

    async def handle(self, query: GetTransactionsQuery) -> list[TransactionResponseDTO]:
        transactions = await self.transaction_repository.get_filtered(
            user_id=query.user_id,
            account_uuid=query.account_uuid,
            offset=query.skip,
            limit=query.limit,
            start_date=query.start_date,
            end_date=query.end_date,
            transaction_type=query.transaction_type,
            category_id=query.category_id,
        )

        if transactions is None:
            raise TransactionNotFoundError(
                f"Not found transactions for account: {query.account_uuid}"
            )

        dtos = [
            TransactionResponseDTO.from_entity(
                transaction,
                account_name,
                account_type,
                cast(str, account_uuid),
                category_name,
            )
            for transaction, account_name, account_type, account_uuid, category_name in transactions
        ]
        await link_security_trades(
            self.security_trade_repository,
            [
                (cast(int, row[0].id), dto)
                for row, dto in zip(transactions, dtos, strict=True)
            ],
        )
        return dtos


async def link_security_trades(
    repository: SecurityTradeRepository | None,
    rows: list[tuple[int, TransactionResponseDTO]],
) -> None:
    """Llena `security_trade_uuid` y `security_holding_uuid` en los movimientos que creó
    una operación de acciones."""
    if repository is None or not rows:
        return
    links = await repository.links_for_transactions([tid for tid, _ in rows])
    for transaction_id, dto in rows:
        link = links.get(transaction_id)
        if link is not None:
            dto.security_trade_uuid = link.trade_uuid
            dto.security_holding_uuid = link.holding_uuid
