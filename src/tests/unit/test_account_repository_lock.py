from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)


@pytest.mark.asyncio
async def test_get_by_uuid_and_user_id_requests_mysql_row_lock_when_requested():
    """El repositorio debe emitir SELECT ... FOR UPDATE para operaciones de saldo."""
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    repository = SQLAlchemyAccountRepository(session)

    await repository.get_by_uuid_and_user_id(
        "account-uuid",
        1,
        for_update=True,
    )

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=mysql.dialect()))

    assert "FOR UPDATE" in sql


@pytest.mark.asyncio
async def test_get_by_uuid_and_user_id_does_not_lock_by_default():
    """Las consultas de lectura deben conservar su comportamiento sin bloqueo."""
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    repository = SQLAlchemyAccountRepository(session)

    await repository.get_by_uuid_and_user_id("account-uuid", 1)

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=mysql.dialect()))

    assert "FOR UPDATE" not in sql
