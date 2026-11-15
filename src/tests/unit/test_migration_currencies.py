"""La migración que pasa las monedas a mayúsculas y se detiene ante una desconocida."""

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "c41d7e2a9b10_normalize_currencies.py"
)


def _migration():
    spec = importlib.util.spec_from_file_location("normalize_currencies", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(rows: dict[str, list[str]]) -> dict[str, list[str]]:
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        for table in ("accounts", "investment_positions"):
            conn.execute(
                sa.text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, currency TEXT)")
            )
            for currency in rows.get(table, []):
                conn.execute(
                    sa.text(f"INSERT INTO {table} (currency) VALUES (:c)"),
                    {"c": currency},
                )
        with Operations.context(MigrationContext.configure(conn)):
            _migration().upgrade()
        return {
            table: [
                c
                for (c,) in conn.execute(
                    sa.text(f"SELECT currency FROM {table} ORDER BY id")
                )
            ]
            for table in ("accounts", "investment_positions")
        }


@pytest.mark.unit
class TestNormalizeCurrencies:
    def test_uppercases_and_trims(self):
        result = _run({"accounts": ["mxn", " usd", "EUR"], "investment_positions": ["Usd"]})
        assert result == {"accounts": ["MXN", "USD", "EUR"], "investment_positions": ["USD"]}

    def test_stops_on_unknown_currencies(self):
        with pytest.raises(RuntimeError) as error:
            _run({"accounts": ["MXN", "gbp", "GBP"], "investment_positions": ["zzz"]})
        message = str(error.value)
        assert "accounts: 'GBP' (2)" in message
        assert "investment_positions: 'ZZZ' (1)" in message
