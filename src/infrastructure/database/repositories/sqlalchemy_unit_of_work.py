from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.application import RepositoryError


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def commit(self):
        try:
            await self._session.commit()
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RepositoryError("commit", "UnitOfWork", str(e)) from e

    async def rollback(self):
        await self._session.rollback()
