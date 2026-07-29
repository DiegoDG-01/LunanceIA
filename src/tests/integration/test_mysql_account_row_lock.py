"""Prueba de integración de bloqueos de fila para MySQL/InnoDB.

Ejecutar con una base de datos exclusiva de pruebas:
MYSQL_TEST_DATABASE_URL='mysql+aiomysql://user:password@host:3306/lunance_test' \
    uv run pytest -q src/tests/integration/test_mysql_account_row_lock.py
"""

import asyncio
import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Column, Integer, MetaData, Numeric, Table, insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


MYSQL_TEST_DATABASE_URL = os.getenv("MYSQL_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not MYSQL_TEST_DATABASE_URL,
    reason="Define MYSQL_TEST_DATABASE_URL para ejecutar la integración con MySQL.",
)


@pytest.mark.asyncio
async def test_mysql_for_update_blocks_a_concurrent_writer():
    """Una segunda transacción no puede bloquear la misma fila hasta el commit."""
    engine = create_async_engine(
        MYSQL_TEST_DATABASE_URL,
        pool_size=2,
        max_overflow=0,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    metadata = MetaData()
    lock_table = Table(
        f"_test_account_lock_{uuid4().hex}",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("balance", Numeric(12, 2), nullable=False),
    )
    first_has_lock = asyncio.Event()
    release_first = asyncio.Event()
    second_has_lock = asyncio.Event()
    first_task = None
    second_task = None

    try:
        async with engine.begin() as connection:
            await connection.run_sync(metadata.create_all)
            await connection.execute(
                insert(lock_table).values(id=1, balance=Decimal("100.00"))
            )

        async def first_transaction() -> None:
            async with session_factory() as session:
                async with session.begin():
                    await session.execute(
                        select(lock_table)
                        .where(lock_table.c.id == 1)
                        .with_for_update()
                    )
                    first_has_lock.set()
                    await release_first.wait()

        async def second_transaction() -> None:
            async with session_factory() as session:
                async with session.begin():
                    await session.execute(
                        select(lock_table)
                        .where(lock_table.c.id == 1)
                        .with_for_update()
                    )
                    second_has_lock.set()

        first_task = asyncio.create_task(first_transaction())
        await asyncio.wait_for(first_has_lock.wait(), timeout=2)

        second_task = asyncio.create_task(second_transaction())
        await asyncio.sleep(0.1)
        assert not second_has_lock.is_set()

        release_first.set()
        await asyncio.wait_for(first_task, timeout=2)
        await asyncio.wait_for(second_task, timeout=2)
        assert second_has_lock.is_set()
    finally:
        release_first.set()
        if first_task and not first_task.done():
            await first_task
        if second_task and not second_task.done():
            await second_task
        async with engine.begin() as connection:
            await connection.run_sync(metadata.drop_all)
        await engine.dispose()
