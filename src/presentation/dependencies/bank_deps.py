from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.banks.queries.get_banks import GetBanksHandler
from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_bank_repository import (
    SQLAlchemyBankRepository,
)


def get_banks_handler(db: AsyncSession = Depends(get_db)) -> GetBanksHandler:
    bank_repository = SQLAlchemyBankRepository(db)
    return GetBanksHandler(bank_repository=bank_repository)
